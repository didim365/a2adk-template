from . import agent

def get_agent(name):
    if name == 'root_agent':
        return agent.root_agent
    else:
        raise ValueError(f'Unknown agent: {name}')