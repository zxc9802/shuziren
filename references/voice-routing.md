# Voice Provider Routing

Ask exactly: **“这次配音使用 MiniMax，还是 HeyGen？”** Do this immediately after authorization and before the company-material question or any script work.

Record only one current-job value:

- **MiniMax (recommended)**: `minimax`
- **HeyGen `voice1`**: `heygen`

Never inherit the previous job's answer. The chosen provider is a routing gate, not a preference hint.

## MiniMax route

1. Verify that the current MiniMax account exposes cloned voice ID `huangxu1`. Do not match by a display name.
2. Before every preview or full-script synthesis, analyze the exact approved text and write a job-specific `voice-plan.json`. Split only at punctuation or true semantic boundaries. Each segment must contain its exact text, semantic role, emotion, emotion intensity, speed, emphasis, and pause direction. Concatenating the segment text must reproduce the approved input losslessly and byte-for-byte.
3. Use `speech-2.8-hd` with `huangxu1` and synthesize according to that plan. Create an amplified but controlled emotional arc: hooks and questions should lift clearly, warnings and reversals should carry substantially more force, explanations should visibly settle, and conclusions should land firmly. When the script contains both high-impact and explanatory beats, target at least `0.45` separation between their emotion intensity values and cap all values at `0.85`. Never flatten every segment to `calm`, and never use shouting, theatrical delivery, or identity-distorting intensity. Preserve approved punctuation as the pause map and never alter the text to manufacture emotion.
4. Generate and join the MP3 segments in approved order, decode the entire result, confirm the expected audio stream and duration, listen to the complete narration, verify the emotional arc is audible without becoming theatrical or distorting the cloned identity, and bind its SHA-256 to the current job.
5. Upload the exact MiniMax audio to HeyGen as the driving audio. HeyGen must not re-synthesize, paraphrase, translate, or rewrite the narration.
6. For a preview, plan and synthesize only the approved opening excerpt. After preview approval, create a new emotion plan for the full approved script, synthesize it, and bind the new full-audio hash separately.

Never silently fall back to HeyGen `voice1`. Stop with the exact blocker when the API credential is unavailable, the voice ID is missing, TTS fails, the returned speech differs from the approved text, the file is invalid, or the exact audio upload cannot be bound.

Do not store API keys, authorization headers, raw provider responses, or temporary URLs in job artifacts.

## HeyGen route

Resolve the private HeyGen `voice1` with `get_voice` from the connected account. Require the exact stable voice ID and expected language; a matching display name is insufficient. Submit the exact approved script through the structured HeyGen avatar or image video tool, with captions off and no undocumented voice settings.

Never silently fall back to MiniMax. Stop when HeyGen `voice1` cannot be verified or bound. Before submission, create the same job-specific `voice-plan.json` from the approved text, preserve its segments losslessly, and carry its emotion, emotion intensity, speed, emphasis, and pause direction into the structured voice direction supported by the endpoint.
