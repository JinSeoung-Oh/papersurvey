import os
from langchain import hub
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

from collections import deque
from datetime import datetime, timezone, timedelta
from PIL import Image
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
import re
from json_repair import repair_json

from dataclasses import dataclass, field
import json
import networkx as nx
from typing import Dict, Any, List, Tuple, Optional
from openai import OpenAI
from langchain.embeddings import OpenAIEmbeddings
import numpy as np
import streamlit as st

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

client = OpenAI()

class O3MiniClient:
    def __init__(self):
        self.client = client
        self.model = "o3-mini"
    def call_as_llm(self, prompt: str) -> str:
        # v1.x 방식: chat.completions.create()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        # 반환 형식은 choices[0].message.content
        return response.choices[0].message.content

class _4oMiniClient:
    def __init__(self):
        self.client = client
        self.model = "gpt-4o"
    def call_as_llm(self, prompt: str) -> str:
        # v1.x 방식: chat.completions.create()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        # 반환 형식은 choices[0].message.content
        return response.choices[0].message.content

@dataclass
class UserProfile:
    user_id: str
    sensory_profile: Dict[str, str] = field(default_factory=dict)
    communication_preferences: Dict[str, str] = field(default_factory=dict)
    stress_signals: List[str] = field(default_factory=list)

class CareGraph:
    FAILURE_THRESHOLD = 5

    def __init__(self, llm: ChatOpenAI):
        self.graph = nx.DiGraph()
        self.llm = llm
        self.situation_counter = 0

    def add_profile(self, profile: UserProfile):
        self.graph.add_node(
            profile.user_id,
            type='user',
            sensory_profile=profile.sensory_profile,
            comm_prefs=profile.communication_preferences,
            stress_signals=profile.stress_signals
        )

    def _situation_node(self, user_id: str, situation_id: int) -> Tuple[str, str, int]:
        return (user_id, 'situation', situation_id)

    def _cause_node(self, user_id: str, situation_id: int, cause: str) -> Tuple[Any, ...]:
        return (user_id, 'cause', situation_id, cause)

    def _intervention_node(
        self, user_id: str, situation_id: int, cause: str, strategy: str
    ) -> Tuple[Any, ...]:
        return (user_id, 'intervention', situation_id, cause, strategy)

    def add_situation(self, user_id: str, text: str) -> int:
        sid = self.situation_counter
        node = self._situation_node(user_id, sid)
        self.graph.add_node(
            node,
            type='situation',
            text=text,
        )
        self.graph.add_edge(user_id, node, relation='HAS_SITUATION')
        self.situation_counter += 1
        return sid

    def add_cause(
        self, user_id: str, situation_id: int, cause: str
    ) -> Tuple[Any, ...]:
        sit_node = self._situation_node(user_id, situation_id)
        if not self.graph.has_node(sit_node):
            raise ValueError('Situation node missing')
        cause_node = self._cause_node(user_id, situation_id, cause)
        if not self.graph.has_node(cause_node):
            self.graph.add_node(
                cause_node,
                type='cause',
                text=cause,
            )
            self.graph.add_edge(sit_node, cause_node, relation='HAS_CAUSE')
        return cause_node

    def add_intervention(
        self,
        user_id: str,
        situation_id: int,
        cause: str,
        intervention: Dict[str, Any]
    ) -> None:
        cause_node = self._cause_node(user_id, situation_id, cause)
        if not self.graph.has_node(cause_node):
            raise ValueError('Cause node missing')
        strategy = intervention.get('strategy', '')
        intr_node = self._intervention_node(
            user_id, situation_id, cause, strategy
        )
        if not self.graph.has_node(intr_node):
            text = (
                f"{strategy} {intervention.get('purpose','')} "
                f"{intervention.get('example','')}"
            ).strip()
            self.graph.add_node(
                intr_node,
                type='intervention',
                strategy=strategy,
                purpose=intervention.get('purpose'),
                example=intervention.get('example'),
                failures=0
            )
            self.graph.add_edge(cause_node, intr_node, relation='HAS_INTERVENTION')

    def list_situations(self, user_id: str) -> List[Dict[str, Any]]:
        results = []
        for _, sit_node, data in self.graph.edges(user_id, data=True):
            if data.get('relation') == 'HAS_SITUATION':
                attrs = self.graph.nodes[sit_node]
                results.append({
                    'situation_id': sit_node[2],
                    'text': attrs.get('text'),
                })
        return results

    def list_events(
        self, user_id: str, situation_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        results = []
        for _, sit_node, data in self.graph.edges(user_id, data=True):
            if data.get('relation') != 'HAS_SITUATION':
                continue
            sid = sit_node[2]
            if situation_id is not None and sid != situation_id:
                continue
            for _, cause_node, cd in self.graph.edges(sit_node, data=True):
                if cd.get('relation') != 'HAS_CAUSE':
                    continue
                cause = cause_node[3]
                for _, intr_node, idata in self.graph.edges(cause_node, data=True):
                    if idata.get('relation') != 'HAS_INTERVENTION':
                        continue
                    attrs = self.graph.nodes[intr_node]
                    results.append({
                        'situation_id': sid,
                        'cause': cause,
                        'strategy': attrs.get('strategy'),
                        'purpose': attrs.get('purpose'),
                        'example': attrs.get('example'),
                        'failures': attrs.get('failures', 0)
                    })
        return results
        
    def _extract_scenario(self, full_text: str) -> str:
        import re
        """
        full_text에서 Setting, Observations, Others/Environment 섹션만
        추출해서 하나의 문자열로 합쳐 반환.
        """
        # Setting
        m_set = re.search(r"Setting:\s*(.*?)(?=\n\n)", full_text, flags=re.DOTALL)
        setting = m_set.group(1).strip() if m_set else ""

        # Observations
        m_obs = re.search(
            r"Observations.*?:\s*(.*?)(?=\n\nOthers/Environment)",
            full_text, flags=re.DOTALL
        )
        observations = m_obs.group(1).strip() if m_obs else ""

        # Others/Environment
        m_oth = re.search(
            r"Others/Environment:\s*(.*?)(?=Consistency Rule:)",
            full_text, flags=re.DOTALL
        )
        others = m_oth.group(1).strip() if m_oth else ""

        # 합친 시나리오
        return "\n\n".join(filter(None, [setting, observations, others]))
        
    def find_similar_events(
        self, user_id: str, text: str
    ) -> Tuple[Optional[int], List[Dict[str, Any]]]:
        # 1) 쿼리 텍스트도 시나리오만 추출
        query_scenario = self._extract_scenario(text)

        best_id = None
        best_sim = -1.0
        for sit in self.list_situations(user_id):
            # sit['text']가 full_text라면 시나리오만 추출
            stored_text = sit['text']
            if isinstance(stored_text, str):
                stored_scenario = self._extract_scenario(stored_text)
            else:
                # 이미 dict라면 필요한 필드 합치기
                stored_scenario = "\n\n".join(filter(None, [
                    stored_text.get("Setting",""),
                    stored_text.get("Observations",""),
                    stored_text.get("Others/Environment","")
                ]))
            prompt = f"""You are a text similarity evaluator. Return a number between 0 (completely different) and 1 (identical)
            Compare these:\n\nA:\n{query_scenario}\n\nB:\n{stored_scenario}. ONLY RETURN SCORE(INT)"""
            
            sim = self.llm.call_as_llm(prompt)
            sim_str = sim.strip()

            m = re.search(r"(\d+\.\d+)", sim_str)
            if not m:
                return None, []
                
            sim_value = float(m.group(1))
            if sim_value > best_sim:
                best_sim = sim
                best_id = sit['situation_id']

        print(f"[RESULT] Best SIM: {best_sim:.4f} | SID: {best_id}")

        if best_id is None or best_sim < 0.8:
            return None, []
            
        events = self.list_events(user_id, situation_id=best_id)
        return best_id, events

    def record_outcome(
        self,
        user_id: str,
        situation_id: int,
        cause: str,
        strategy: str,
        success: bool
    ) -> bool:
        intr_node = self._intervention_node(
            user_id, situation_id, cause, strategy
        )
        if not self.graph.has_node(intr_node):
            return False
        if success:
            self.graph.nodes[intr_node]['failures'] = 0
            return False
        self.graph.nodes[intr_node]['failures'] = (
            self.graph.nodes[intr_node].get('failures', 0) + 1
        )
        if self.graph.nodes[intr_node]['failures'] >= CareGraph.FAILURE_THRESHOLD:
            self.graph.remove_node(intr_node)
            return True
        return False


class MemoryAgent:
    def __init__(
        self,
        llm: ChatOpenAI,
        cg: CareGraph
    ):
        self.llm = llm
        self.cg = cg
        self.history: List[Tuple[str, str]] = []

    def _parse_json(self, resp: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(resp)
        except json.JSONDecodeError:
            return None

    def _profile_ctx(self, user_id: str) -> str:
        attrs = self.cg.graph.nodes[user_id]
        return (
            f"학생 프로필:\n"
            f"- 감각 프로필: {attrs.get('sensory_profile')}\n"
            f"- 의사소통 선호: {attrs.get('comm_prefs')}\n"
            f"- 선호 완화 전략: {attrs.get('preference')}\n"
            f"- 스트레스 신호: {attrs.get('stress_signals')}\n\n"
        )

    def graph_ask(
        self,
        user_id: str,
        user_input: str,
        similar_events: str,
        user_profile: str
    ) -> str:
        prompt = (
            self._profile_ctx(user_id) +
            f"{user_input}을 철저하게 수행해주세요" + 
            "**event** 및 **observed_behavior** 그리고 **intervention_strategies**을 포함하여 구체적인 JSON 리스트로 제시하세요." + 
            "각 전략은 돌봄 교사가 즉시 현장에서 사용할 수 있어야 하며 단계별 예시를 포함해야 합니다." +
            f"전략 수립 시에 과거 중재에 성공한적이 있는 {similar_events}를 참고하여 {user_input}에 알맞게 전략 수립 후에 제시해주세요." +
            f"당신이 수립한 전략은 일반적인 전략이 아닌 {user_profile}에 가장 알맞은 전략이어야만 합니다. 그렇지 않은 답변은 리턴하지 마세요." +
            "멜트 다운 상황에 대한 예방적인 방안을 immediate에 넣지 마세요. immediate는 멜트 다운 상황을 해결하기 위한 즉각적이고 현실적인 방안이어야만 합니다." + 
            "주어진 정보를 주관적으로 해석하거나 주어지지 않은 쓸데 없는 정보를 추가 하지 마세요."+
            "반드시 한국어로 답하세요"
        )
        response = self.llm.call_as_llm(prompt)
        return response
    
    def initial_ask(
        self,
        user_id: str,
        user_input: str,
        situation: str
    ) -> Tuple[int, str]:
        sid = self.cg.add_situation(user_id, situation)
        prompt = (
            self._profile_ctx(user_id) +
            "오직 사용자 요청에 맞춰 **원인과 중재 전략**을 매우 자세하게 한국어로 알려주세요. "
            "상황별 event 이름을 키로 하고 cause·intervention을 포함한 JSON을 제시하세요." 
            "반드시 한국어로 답하세요\n" +
            f"요청:\n{user_input}\n"
        )
        return sid, self.llm.call_as_llm(prompt)

    def alt_ask(
        self,
        user_id: str,
        user_feedback: str,
        failed_event: str,
        user_profile: str,
        situation: str,
    ) -> str:
        prompt = (
            f"문제 상황: {situation}" + "\n"
            f"이전 전략 '{failed_event}'가 실패했습니다. 사용자 피드백: {user_feedback}. " + "\n"
            f"자폐인 프로파일 : {user_profile}" + "\n"
            "주어진 이전 전략은 문제 상황을 해결하지 못 하였습니다. 사용자 피드백과 자폐인 프로파일을 반영하여 새로운 중재 전략을 제시해주세요" +
            "**event** 및 **observed_behavior** 그리고 **intervention_strategies**을 포함하여 구체적인 JSON 리스트로 제시하세요." +
            "각 전략은 돌봄 교사가 즉시 현장에서 사용할 수 있어야 하며 단계별 예시를 포함해야 합니다." +
            f"전략 수립 시에 {user_feedback}을 최우선으로 고려하여 전략 수립 후에 제시해주세요." +
            f"당신이 수립한 전략은 {user_profile}에 가장 알맞은 전략이어야만 합니다. 그렇지 않은 답변은 리턴하지 마세요." +
            "immediate에는 그 상황에서 즉각적으로 할 수 있는 현실적인 것이어야만 합니다." + 
            "주어진 정보를 주관적으로 해석하거나 주어지지 않은 쓸데 없는 정보를 추가 하지 마세요."+
            "반드시 한국어로 답하세요"
        )
        response = self.llm.call_as_llm(prompt)
        print(response)
        return response

    def ask(
        self,
        user_id: str,
        user_input: str,
        situation: str
    ) -> str:
        sid, events = self.cg.find_similar_events(user_id, situation)
        if sid is not None and events:
            # Existing memory: do not prompt here
            return ''
        sid, resp = self.initial_ask(user_id, user_input, situation)
        self.history.append((user_input, resp))
        return resp

    def init_feedback_and_retry(
        self,
        user_id: str,
        failed_event: str,
        user_profile: str,
        situation: str,
    ) -> str:
        # 1) Ask simple success/failure
        sid = failed_event['situation_id']
        cause = failed_event['cause']
        strategy = failed_event['strategy']
        
        ok = input(f"전략이 성공적이었나요? (y/n): ")
        if ok.strip().lower().startswith('y'):
            # Decrease failure count
            self.cg.record_outcome(user_id, sid, cause, strategy, success=True)
            return "성공으로 기록했습니다."
        # 2) On failure, get detailed feedback
        detail = input("실패 이유나 조치 후 자폐인의 반응 등을 구체적으로 입력해주세요: ")
        self.cg.record_outcome(user_id, sid, cause, strategy, success=False)
        return self.alt_ask(user_id, detail, failed_event, user_profile,situation)

    def feedback_and_retry(
        self,
        user_id: str,
        failed_event: str,
        user_profile: str,
        situation: str,
    ) -> str:
        # 1) Ask simple success/failure
        ok = input(f"전략이 성공적이었나요? (y/n): ")
        if ok.strip().lower().startswith('y'):
            return "Complete"
        # 2) On failure, get detailed feedback
        detail = input("실패 이유나 조치 후 자폐인의 반응 등을 구체적으로 입력해주세요: ")
        return self.alt_ask(user_id, detail, failed_event, user_profile, situation)

    def finalize(self, user_id: str):
        if not self.history:
            return
        last_resp = self.history[-1][1]
        data = self._parse_json(last_resp)
        print('finzalize', data)
        if not data or 'action_input' not in data:
            return

        sid = self.cg.situation_counter - 1
        action_input = data['action_input']

        for evt, detail in action_input.items():
            cause = detail.get('cause') or ''
            interventions = detail.get('intervention') or []
            if not cause or not interventions:
                continue

            print(f"\n이벤트: {evt}")
            for i, intr in enumerate(interventions, start=1):
                print(f"  {i}. {intr.get('strategy')}")
            choice = input("적용하신 전략의 번호를 입력하세요: ").strip()
            try:
                idx = int(choice) - 1
                chosen = interventions[idx]
            except (ValueError, IndexError):
                print("저장 하지 않음")
                continue

            # 구조화된 저장 로직
            self.cg.add_cause(user_id, sid, cause)
            self.cg.add_intervention(user_id, sid, cause, chosen)
            print(
                f"저장 완료: situation={sid}, cause='{cause}', strategy='{chosen.get('strategy')}'"
            )
