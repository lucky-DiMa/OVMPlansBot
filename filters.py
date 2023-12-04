from classes import PlansBotUser


class StateFilter:
    def __init__(self, checking_state: str, startswith: bool = False):
        self.checking_state = checking_state
        self.startswith = startswith

    def __call__(self, _: None = None, user: PlansBotUser | None = None) -> bool:
        return user.state.startswith(self.checking_state) if self.startswith else (self.checking_state == user.state)