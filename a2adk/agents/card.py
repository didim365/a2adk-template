from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

def get_agent_card(host: str, port: int) -> AgentCard:
    skill = AgentSkill(
        id='plan_parties',
        name='Plan a Birthday Party',
        description='Plan a birthday party, including times, activities, and themes.',
        tags=['event-planning'],
        examples=[
            'My son is turning 3 on August 2nd! What should I do for his party?',
            'Can you add the details to my calendar?',
        ],
    )

    return AgentCard(
        name='Birthday Planner',
        description='I can help you plan fun birthday parties.',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
