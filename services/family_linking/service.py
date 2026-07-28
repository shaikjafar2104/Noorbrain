from __future__ import annotations
from typing import Any
from services.family_ai.store import family_store
from services.face_identity.store import face_identity_store

class FamilyLinkingService:
    def list_links(self) -> dict[str, Any]:
        profiles = list(family_store.read().get("profiles", []))
        persons = face_identity_store.list_persons()
        linked_profiles=set(); links=[]
        for person in persons:
            profile_id=person.get("family_profile_id")
            profile=next((p for p in profiles if str(p.get("id"))==str(profile_id)),None)
            if profile: linked_profiles.add(str(profile["id"]))
            links.append({"person_id":person.get("id"),"person_name":person.get("name"),"sample_count":person.get("sample_count",0),"family_profile_id":profile_id,"family_profile":profile,"linked":profile is not None})
        unknown=[e for e in face_identity_store.list_events(limit=500) if not e.get("recognized")]
        return {"status":"ok","link_count":sum(1 for x in links if x["linked"]),"person_count":len(persons),"profile_count":len(profiles),"unknown_event_count":len(unknown),"links":links,"unlinked_profiles":[p for p in profiles if str(p.get("id")) not in linked_profiles],"unknown_events":unknown[:100]}

    def link(self, *, person_id:str, profile_id:str) -> dict[str,Any]:
        fdata=family_store.read(); profile=next((p for p in fdata.get("profiles",[]) if str(p.get("id"))==str(profile_id)),None)
        if profile is None: raise KeyError("Family profile not found.")
        payload=face_identity_store._read(); person=next((p for p in payload["persons"] if str(p.get("id"))==str(person_id)),None)
        if person is None: raise KeyError("Face person not found.")
        person["family_profile_id"]=profile_id; face_identity_store._write(payload)
        for p in fdata.get("profiles",[]):
            if str(p.get("id"))==str(profile_id): p["face_person_id"]=person_id
        family_store.write(fdata)
        return {"status":"linked","person_id":person_id,"profile_id":profile_id,"person_name":person.get("name"),"profile_name":profile.get("name")}

    def unlink(self, person_id:str) -> dict[str,Any]:
        payload=face_identity_store._read(); person=next((p for p in payload["persons"] if str(p.get("id"))==str(person_id)),None)
        if person is None: raise KeyError("Face person not found.")
        old=person.get("family_profile_id"); person["family_profile_id"]=None; face_identity_store._write(payload)
        fdata=family_store.read()
        for p in fdata.get("profiles",[]):
            if str(p.get("face_person_id"))==str(person_id): p["face_person_id"]=None
        family_store.write(fdata)
        return {"status":"unlinked","person_id":person_id,"old_profile_id":old}

    def auto_link(self) -> dict[str,Any]:
        profiles=family_store.read().get("profiles",[]); created=[]
        for person in face_identity_store.list_persons():
            if person.get("family_profile_id"): continue
            name=str(person.get("name") or "").strip().casefold()
            profile=next((p for p in profiles if str(p.get("name") or "").strip().casefold()==name),None)
            if profile: created.append(self.link(person_id=str(person["id"]), profile_id=str(profile["id"])))
        return {"status":"ok","created_count":len(created),"links":created}

family_linking_service=FamilyLinkingService()
