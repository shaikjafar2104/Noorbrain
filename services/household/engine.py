"""Privacy-conscious household summaries over learning events."""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from typing import Any,Dict,List,Optional
class HouseholdEngine:
    def __init__(self,store:Any)->None:self.store=store
    def _events(self,days:int=7):return self.store.list_events(limit=10000,start_at=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat())
    def members(self,days:int=30)->Dict[str,Any]:
        events=self._events(days); data=defaultdict(lambda:{"events":0,"rooms":Counter(),"types":Counter()})
        for e in events:
            p=e.get("person_id") or "unassigned"; data[p]["events"]+=1
            if e.get("room"):data[p]["rooms"][e["room"]]+=1
            data[p]["types"][e["event_type"]]+=1
        members=[]
        for p,v in sorted(data.items()): members.append({"person_id":p,"event_count":v["events"],"top_room":v["rooms"].most_common(1)[0][0] if v["rooms"] else None,"top_activity":v["types"].most_common(1)[0][0] if v["types"] else None})
        return {"status":"ok","days":days,"member_count":len(members),"members":members}
    def timeline(self,days:int=1,limit:int=200)->Dict[str,Any]:
        events=self._events(days)[:limit]
        return {"status":"ok","days":days,"count":len(events),"timeline":[{"occurred_at":e["occurred_at"],"person_id":e.get("person_id") or "unassigned","room":e.get("room"),"event_type":e["event_type"],"source":e["source"]} for e in events]}
    def summary(self,days:int=7)->Dict[str,Any]:
        events=self._events(days); rooms=Counter(e.get("room") for e in events if e.get("room")); types=Counter(e["event_type"] for e in events); people=Counter(e.get("person_id") or "unassigned" for e in events)
        return {"status":"ok","service":"household","sprint":"9.4","days":days,"total_events":len(events),"active_people":len(people),"most_active_room":rooms.most_common(1)[0][0] if rooms else None,"most_common_activity":types.most_common(1)[0][0] if types else None,"events_by_room":dict(rooms.most_common(20)),"events_by_person":dict(people.most_common(20)),"events_by_type":dict(types.most_common(20))}
    def shared_reminders(self,days:int=30)->Dict[str,Any]:
        events=self._events(days); reminder=Counter()
        for e in events:
            if "reminder" in e["event_type"] or "prayer" in e["event_type"]: reminder[(e["event_type"],e.get("room") or "any")]+=1
        suggestions=[{"event_type":k[0],"room":k[1],"historical_count":v,"suggestion":"consider_shared_reminder"} for k,v in reminder.most_common(10) if v>=2]
        return {"status":"ok","days":days,"suggestion_count":len(suggestions),"suggestions":suggestions}
