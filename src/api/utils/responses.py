def build_response(task_id: str, message: str = "", result=None, error=None) -> dict:
    response = {
        "status": "Task submitted" if not result and not error else (
            "completed" if result else "failed"
        ),
        "task_id": task_id,
        "message": message
    }
    if result:
        response["result"] = result
    if error:
        response["error"] = error
    return response
