(()=>{
"use strict";

function openRules(){
  if(window.NoorIslamicRuleCreatorV12?.open){
    window.NoorIslamicRuleCreatorV12.open();
    return true;
  }

  console.warn(
    "Islamic Rule Creator is not ready."
  );

  return false;
}

function text(el){
  return String(
    el?.textContent || ""
  ).trim().toLowerCase();
}

function isSmartRuleTarget(el){
  if(!el) return false;

  const page=String(
    el.dataset?.page || ""
  ).toLowerCase();

  const module=String(
    el.dataset?.module || ""
  ).toLowerCase();

  const action=String(
    el.dataset?.action || ""
  ).toLowerCase();

  const t=text(el);

  if(
    page==="islamic-smart-rules" ||
    page==="smart-islamic-rules" ||
    module==="islamic-smart-rules" ||
    action==="islamic-smart-rules"
  ){
    return true;
  }

  return (
    t==="islamic rules" ||
    t==="islamic smart rules" ||
    t==="smart islamic rules" ||
    t==="create smart rule"
  );
}

document.addEventListener(
  "click",
  event=>{
    const target=event.target.closest(
      "button,a,[data-page],[data-module],[data-action]"
    );

    if(!isSmartRuleTarget(target)){
      return;
    }

    /*
      Do not hijack the old Reminder Rules page.
      Only explicit Islamic Smart Rule targets.
    */
    const page=String(
      target.dataset?.page || ""
    ).toLowerCase();

    if(page==="reminder-rules"){
      return;
    }

    if(openRules()){
      event.preventDefault();
      event.stopPropagation();
    }
  },
  true
);

window.NoorIslamicRuleNavV12={
  open:openRules
};

console.log(
  "NOOR_ISLAMIC_RULE_NAV_V12_READY"
);
})();
