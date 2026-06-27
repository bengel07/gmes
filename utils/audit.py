from models import AuditLog
import time
from extensions import db
from flask import request, session
from datetime import datetime
import json

def log_action(
        action,
        user_id=None,
        button_id=None,
        request_data=None,
        response_status=200,
        error_message=None,
        duration_ms=None):

    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            session_id=session.get("session_id"),
            page_url=request.url,
            button_id=button_id,
            request_method=request.method,
            request_data=json.dumps(request_data) if request_data else None,
            response_status=response_status,
            duration_ms=duration_ms,
            browser=request.user_agent.browser,
            os=request.user_agent.platform,
            error_message=error_message
        )

        db.session.add(log)
        db.session.commit()

    except Exception as e:
        print("Erreur Audit:", e)