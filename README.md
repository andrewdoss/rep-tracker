# rep-tracker
Hands-free rep tracking for common exercises using Alexa

# Contents
This project is a quick POC and has several TODOs that I may or may not get to:
- Write docs, including how to deploy.
- Automated tests.
- Add user-device auth/relations and support isolated multi-user data.
- Add rep history report query with csv dump to public S3 for hydrating TBD JS/D3 dashboard.
- Voice configuration of supported exercises.
- Improved dialog
    - Track multiple exercises in one utterance.
    - Reprompt for missing slots.
    - Allow user-specified rep aggregation windows, e.g. "this week" rather than just today.
- Optimizations - reuse connections for warm lambda calls. 
