# Demo Video Script (target 4:00, limit 3–5 min)

**Setup before recording**
- Run `python -m uvicorn main:app --port 8000`, open Chrome at 1920×1080 and zoom the browser to 90%.
- Pre-load each screen once so the first load is warm, then go back to Overview with `?intro=1` to play the logo intro.
- Record with OBS or Windows Game Bar (Win + G). Use a quiet room and a headset mic.
- Everything shown is live model output, so numbers may differ slightly if you change the time or area. Read them off the screen rather than from this script.

| Time | Screen / action | Voice-over |
|---|---|---|
| **0:00–0:20** | Overview with `?intro=1`: logo intro plays | "Pune measures its air every hour. What it can't do is test a decision before making it. Should we cut traffic, curb construction dust, or stop waste burning? Which one actually helps, and where? This is UrbanAir Twin." |
| **0:20–0:55** | **Observe.** Overview map. Toggle *Stations*, *Traffic corridors*, *Industrial zones*. Hover the heat map. Point at the red isoline. | "We fuse CPCB, MPCB and IITM stations with ERA5 weather, the ARAI traffic survey and the emission inventory. Twelve stations become a 500-metre modeled grid of almost 3,800 cells, so neighbourhoods with no monitor still get an estimate. The red line marks the hotspot boundary above the CPCB 24-hour standard. Faded areas are where the model is extrapolating, and we show that openly." |
| **0:55–1:35** | **Explain.** Hotspots. Click the hottest cell near Pimpri-Chinchwad, then the Hadapsar station. | "Click any cell and the twin explains its estimate. TreeSHAP shows which inputs the model relied on, grouped into traffic, industry, dust, burning and meteorology. Here, industry and burning push this cell above average. We call it a model-attributed contribution, not proof of cause, and the traffic, industry, dust and burning inputs are labelled as proxies." |
| **1:35–2:15** | **Predict.** Forecast for Revenue Colony-Shivajinagar. Hover the band, point at the observed dots. Scroll to the skill table and the Day +1/+2/+3 cards. | "The forecast runs 72 hours ahead. The green line is the forecast, the band is our 10-to-90 percent range, and the amber dots are what the sensors actually measured. On held-out 2025 data it beats persistence at 6, 48 and 72 hours. At 24 hours it doesn't, and we show that too. Below: how much of the city crosses the standard each of the next three days." |
| **2:15–3:15** | **Simulate.** Scenario Lab. Area: Shivajinagar, 3 km, 18:00 + 4 h. Traffic −20%, press **Run**. Read the output table. Toggle Baseline / Scenario / **Change**. Then press **Combined** and **Run** again. | "Now the part no dashboard has. What if evening-peak traffic around Shivajinagar drops 20 percent? The twin re-runs the same trained model on every cell and compares it with the baseline: mean PM2.5, hotspot area, population exposed, traffic share. The Change map shows where the improvement lands, and it's uneven. That's the useful finding: a citywide rule helps some wards much more than others. If a slider pushes an input outside what the model has seen, it warns us." |
| **3:15–3:45** | **Decide.** Choose 20%, press **Rank interventions**. | "Finally, Decide. Each lever is applied alone at the same strength over the same area and window, then ranked by how much it lowers PM2.5 and shrinks the hotspot. For Hadapsar this evening, open-burning control comes first, about twice the effect of an equal traffic cut." *(point at rank 1, then switch the area to Shivajinagar and rank again)* "Shivajinagar gets a different answer: industry. One city, different cures, and a citywide rule would miss that." |
| **3:45–4:00** | Scroll to *Model validation*, then cut to the GitHub repo README. | "Every number here comes from data or the model, and is labelled observed or modeled. Next we'll add live traffic counts, satellite data and a population layer for one ward pilot. UrbanAir Twin: other tools tell you the air is bad. We help you decide what to do about it." |

**Tips**
- Keep the cursor slow and deliberate, and pause for about one second after each click so the viewer sees the result.
- If a run takes more than 2 s, cut the wait in editing.
- Add captions for the key numbers in editing; judges often watch muted.
- Export at 1080p MP4 and check the length is under 5:00.
