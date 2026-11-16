# KaiContinuity integration

KaiContinuity persists KaiOperator's JSON-compatible state locally, restores it on restart, and rebuilds the recommendation engine for an awakened operator.

Set `KAI_CONTINUITY_DIR` to a writable local directory to enable automatic checkpoints, or instantiate `KaiOperator(continuity_dir="/path/to/private/state")`. Without either setting, the original in-memory behavior remains unchanged.

Run `python -m unittest discover -s tests -p 'test_kai_continuity.py' -v`.

This integration covers only KaiOperator's explicit fields. It does **not** migrate historical conversations, connect to AI Arena, enable model switching, or prove offline behavior of the web app. Never commit the state directory or personal data. If an existing checkpoint is invalid, recovery may use the previous valid checkpoint; otherwise the operator starts without claiming recovery.
