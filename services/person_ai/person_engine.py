class PersonEngine:
    def __init__(self):
        self.version = "Sprint 5.0"
        self.status = "ready"

    def status_info(self):
        return {
            "status": self.status,
            "version": self.version,
            "known_people": 0,
            "recognized_people": 0,
            "current_person": None,
        }


person_engine = PersonEngine()
