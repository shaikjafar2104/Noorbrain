from __future__ import annotations
from typing import Any
from fastapi import APIRouter
from .completion import sprint11_completion
from .final_qa import automation_final_qa
router=APIRouter(prefix='/api/automation/final', tags=['Automation Final QA'])
@router.get('/health')
def final_health()->dict[str,Any]: return {'status':'healthy','service':'automation_final'}
@router.post('/qa/run')
def run_final_qa()->dict[str,Any]: return automation_final_qa.run()
@router.get('/qa/report')
def final_qa_report()->dict[str,Any]: return automation_final_qa.run()
@router.get('/completion')
def completion_status()->dict[str,Any]: return sprint11_completion.status()
@router.post('/completion/mark')
def mark_completion()->dict[str,Any]: return sprint11_completion.write_marker()
