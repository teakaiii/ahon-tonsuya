# AHON FloodWatch Quality Evaluation Plan

## Purpose and Scope

This is a project-specific evaluation plan informed by the ISO/IEC 25010:2023 product quality model. It is not an ISO certification, conformity assessment, or claim that the system complies with every standard requirement. The defense team should execute the tests, record actual evidence, and report limitations honestly.

Evaluate the web dashboard, Django API, Arduino sensor/serial bridge, and SMS alert workflow as one system. Do not test SMS delivery against real residents without consent; use an approved test recipient and controlled sensor inputs.

## Evaluation Matrix

For every test, record the date, tester, build/firmware version, test data, observed result, and evidence path. Mark a result only after executing the test.

| ISO/IEC 25010:2023 characteristic | AHON FloodWatch evaluation | Suggested acceptance evidence | Result |
| --- | --- | --- | --- |
| Functional suitability | Verify login/roles, current level, history, threshold states, alert logging, recipient configuration, SMS triggers, and `/api/dashboard/water-level-forecast/`. Automated forecast tests cover authentication, insufficient data, out-of-range filtering, and forecast/baseline metric fields. | Automated evidence: `apps.dashboard.tests` (5 tests passed). Manual evidence is still needed for SMS delivery, recipient EEPROM behavior, and sensor boundary inputs at 1.99, 2.00, 2.99, and 3.00 cm. | Forecast tests passed; full system matrix not yet measured |
| Performance efficiency | Measure API response times, dashboard refresh delay, and behavior while exporting or charting a representative dataset. | Record response-time distribution, dataset size, and test machine; agree project-specific limits before testing. | Not yet measured |
| Compatibility | Exercise the supported browser and screen sizes; verify Arduino USB serial and backend API integration on the defense machine. | Browser/OS/device matrix with successful workflow evidence and any known limitations. | Not yet measured |
| Interaction capability | Ask representative users to identify the current flood state, read the latest level, find GSM/sensor health, and follow the relevant response guidance. | Task completion, observed errors, and participant feedback; document participant count and consent. | Not yet measured |
| Reliability | Simulate unplugged/reconnected USB serial, delayed or malformed readings, backend interruption, and SMS modem rejection/retry. | Recovery behavior, missing-data handling, logs, and successful reconnect evidence; verify no false `connected` claims. | Not yet measured |
| Security | Test authenticated and unauthorized API access, role restrictions, secret handling, and repository contents before sharing. The forecast endpoint test verifies unauthenticated requests are rejected. | Automated evidence: `apps.dashboard.tests` includes 401 for unauthenticated forecast access. Still record role tests and confirm real `.env`, credentials, and database files are excluded from Git. | Forecast authentication test passed; full security review not yet measured |
| Maintainability | Run focused automated tests, frontend build/lint where configured, Django system checks, and review setup instructions. | Commands, versions, pass/fail output, and known pre-existing failures. | Not yet measured |
| Flexibility | Change an approved recipient and sensor calibration/configuration, restart components, and verify persistence and consistent thresholds. | Configuration-change procedure and before/after evidence; identify values still fixed in firmware. | Not yet measured |
| Safety | Verify Danger escalation wording and delivery path with a controlled test; verify behavior for stale, invalid, or out-of-range sensor data. | Test log showing safe handling, escalation, and human-response guidance. State that forecasts are advisory and never the sole evacuation trigger. | Not yet measured |

## Current Sensor Reference

The current sketch calibration maps ADC 0-600 to approximately 0-4 cm. Its two operational boundaries are ADC 300 = 2 cm (Warning) and ADC 450 = 3 cm (Critical/Danger). Normal is below 2 cm. These values are valid only for the current sensor calibration and must be re-measured if the hardware or installation changes.

## Reporting Template

For each characteristic, report:

- Test case and setup
- Expected result
- Observed result and measured value
- Pass, fail, or not tested
- Evidence filename or screenshot
- Limitation and corrective action

Do not convert unexecuted checklist items into a passing score. A small demonstration dataset is not enough to establish dependable flood forecasting; report the Colab notebook's chronological holdout MAE/RMSE/R-squared alongside the dataset span and quality exclusions, and describe the forecast as exploratory until validated with longer, representative field data.
