from vorta.store.models import EventLogModel

class LogPageViewModel:
    def get_event_logs(self,profile_id):
        """Fetch event logs for a specific profile, ordered from newest to oldest."""
        event_logs = [
            s
            for s in EventLogModel.select()
            .where(EventLogModel.profile == profile_id)
            .order_by(EventLogModel.start_time.desc())
        ]
        return event_logs
