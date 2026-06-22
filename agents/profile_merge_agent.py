from graph.state import InterviewState


def profile_merge_node(state: InterviewState):
    role = (
        state.get("ambiguity_role")
        or state.get("role")
    )

    experience_level = (
        state.get("ambiguity_experience_level")
        or state.get("experience_level")
    )

    company = state.get("company")

    return {
        "role": role,
        "experience_level": experience_level,
        "company": company,
    }