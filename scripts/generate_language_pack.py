"""Generate data/language_pack_examples.json — run once or when expanding examples."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "language_pack_examples.json"


def ex(id_: str, tone: str, trigger: str, response: str, inp: str | None = None) -> dict:
    return {"id": id_, "input": inp or trigger, "trigger": trigger, "tone": tone, "response": response}


def main() -> None:
    humorous = [
        ex("hum-001", "humorous", "replying to everyone", "Holster the dynamite — write the rant privately, then drop one meme-level reply."),
        ex("hum-002", "humorous", "everyone is clowning me", "Clown energy detected — turn it into a fun-sized post instead of a meltdown."),
        ex("hum-003", "humorous", "reply to every hater", "Replying to every hater is a full-time job — riff privately, then ping one safe joke."),
        ex("hum-004", "humorous", "meltdown incoming", "Meltdown energy spotted — holster the dynamite and post the fun-sized version."),
        ex("hum-005", "humorous", "rant thread brewing", "Draft the rant thread privately — drop one micro-meme, not the whole season finale."),
        ex("hum-006", "humorous", "main character moment", "Main-character energy is loud — nudge it into a tiny chaos post, not a demolition."),
        ex("hum-007", "humorous", "worst day ever online", "Worst-day comedy of errors — write the rant, meme one line, close the tab."),
        ex("hum-008", "humorous", "comedy of errors posting", "Fun-sized chaos only — poke the idea privately before you spark a public spiral."),
        ex("hum-009", "humorous", "venting at strangers", "Vent in a private note — strangers get one soft joke, not the full script."),
        ex("hum-010", "humorous", "clown energy in comments", "Too much clown in the comments — riff offline, reply with one safe joke."),
        ex("hum-011", "humorous", "tempted to drag everyone", "Drag energy is tempting — holster it and drop one meme-level reply instead."),
        ex("hum-012", "humorous", "season finale energy", "No season finale today — write the rant privately, post the fun-sized version."),
        ex("hum-013", "humorous", "dynamite in the replies", "Dynamite in the replies? Holster it — ping one line and log off."),
        ex("hum-014", "humorous", "everyone hates my post", "Heat on the post stings — riff privately, then one micro-meme if you still want to respond."),
        ex("hum-015", "humorous", "ratio incoming", "Ratio panic is real — poke a private draft, not a public war."),
        ex("hum-016", "humorous", "quote tweeting haters", "Quote-tweeting haters is a trap — meme privately, nudge one calm boundary."),
        ex("hum-017", "humorous", "screaming into the void", "Scream in a private note — the void gets a fun-sized post, not the meltdown."),
        ex("hum-018", "humorous", "so done with this app", "Done energy is valid — spark one tiny draft before you rage-quit the app."),
        ex("hum-019", "humorous", "roast battle starting", "Roast battle loading — write the burns privately, drop one soft joke publicly."),
        ex("hum-020", "humorous", "meme war with strangers", "Meme war with strangers? Fun-sized chaos only — one ping, then peace."),
    ]
    direct = [
        ex("dir-001", "direct", "I'm deleting everything", "Stop. Draft, don't delete. Pick one reversible move and breathe."),
        ex("dir-002", "direct", "quit forever", "Pause before the forever move — draft the next step, not the final action."),
        ex("dir-003", "direct", "burn it all down", "Stop the irreversible move — redirect into a draft version first."),
        ex("dir-004", "direct", "nuking my account", "Account nuke impulse is loud — pick one safe step and draft, don't delete."),
        ex("dir-005", "direct", "wiping all my posts", "Wiping posts is permanent — reset with a parking-lot folder, one reversible move."),
        ex("dir-006", "direct", "walk away forever", "Walk-away energy is real — pause and write the next step, not goodbye."),
        ex("dir-007", "direct", "trashing the whole project", "Trash impulse hits hard — cut nothing yet; draft one paragraph instead."),
        ex("dir-008", "direct", "done forever with publishing", "Forever-quit is a big swing — draft a tiny test post before you bail."),
        ex("dir-009", "direct", "screw this platform", "Intensity is valid — stop, reset, pick one reversible action on-platform."),
        ex("dir-010", "direct", "irreversible delete impulse", "Irreversible delete urge — draft first, decide later."),
        ex("dir-011", "direct", "deleting my draft folder", "Draft folder panic — move files to a parking lot, don't delete."),
        ex("dir-012", "direct", "never posting again deleting all", "Never-again energy — write the next step, not the nuclear option."),
        ex("dir-013", "direct", "reply all disaster", "Reply-all disaster brewing — stop, draft privately, one reversible send."),
        ex("dir-014", "direct", "burning bridges publicly", "Public bridge-burning stings later — draft the heat, post a tiny test instead."),
        ex("dir-015", "direct", "destroying my portfolio", "Portfolio destroy impulse — pause, one safe step, draft version only."),
        ex("dir-016", "direct", "walking away from everything I built", "Walking away from the build hurts — redirect into one reversible move."),
        ex("dir-017", "direct", "can't undo send panic", "Send panic is real — stop before the irreversible move hits send."),
        ex("dir-018", "direct", "quitting and deleting account", "Quit-and-delete combo — draft, don't delete. One safe step first."),
        ex("dir-019", "direct", "wipe everything and bail", "Wipe-and-bail urge — pick one reversible move before you cut."),
        ex("dir-020", "direct", "final meltdown post then delete", "Meltdown-then-delete plan — post a tiny test, not the finale."),
    ]
    strategic = [
        ex("str-001", "strategic", "algorithm hates me", "The algorithm isn't mad — the signal dipped. Test one variable and post a tiny version."),
        ex("str-002", "strategic", "reach tanked", "Reach tanked — this spike is data. Run a micro-experiment and post the tiny version."),
        ex("str-003", "strategic", "metrics dropped", "Metrics dropped — sample one variable and share the data spike with your circle."),
        ex("str-004", "strategic", "engagement crashed", "Engagement crashed — adjust one factor and post a seed, not a spiral."),
        ex("str-005", "strategic", "funnel broken", "Funnel feels broken — measure one step and try a controlled experiment post."),
        ex("str-006", "strategic", "platform punished my post", "Signal dip, not a verdict — test hook or timing and post the small version."),
        ex("str-007", "strategic", "conversion rate collapsed", "Conversion collapsed — one micro-experiment beats one crashout."),
        ex("str-008", "strategic", "test failed badly", "Failed test = data — adjust one variable and post the tiny version."),
        ex("str-009", "strategic", "analytics look terrible", "Analytics sting — sample one metric and share a tiny insight with your circle."),
        ex("str-010", "strategic", "audience not responding", "Audience quiet — post a seed thread and test one variable publicly."),
        ex("str-011", "strategic", "pivot not working", "Pivot friction is data — measure one change and post the fun-sized version."),
        ex("str-012", "strategic", "launch flopped", "Launch flop hurts — log the signal and run one micro-experiment post."),
        ex("str-013", "strategic", "shadowbanned maybe", "Reach mystery — test one variable before you bail on the platform."),
        ex("str-014", "strategic", "impressions in the gutter", "Impressions dipped — this spike is data. Post a tiny version and measure."),
        ex("str-015", "strategic", "strategy isn't working", "Strategy stall — adjust one lever and share a small piece with your circle."),
        ex("str-016", "strategic", "experiment failed", "Experiment failed — sample the data and post one controlled test."),
        ex("str-017", "strategic", "platform reach died", "Reach died — test timing or format and post the seed, not the rant."),
        ex("str-018", "strategic", "post tanked overnight", "Overnight tank is data — one variable test beats spiraling offline."),
        ex("str-019", "strategic", "metrics spiral", "Metrics spiral — measure one thing and turn it into a micro-thread."),
        ex("str-020", "strategic", "algorithm change ruined reach", "Algorithm shift stings — post a tiny version and test one variable."),
    ]
    calm = [
        ex("calm-001", "calm", "I'm overwhelmed", "Take a breath — write the first line only. Ease the moment."),
        ex("calm-002", "calm", "spiraling anxious", "Spiral energy is real — soften with one gentle draft and a soft step."),
        ex("calm-003", "calm", "can't breathe panic", "Panic spike — breathe, ground, write the first line only."),
        ex("calm-004", "calm", "everything feels sharp", "Sharp moment — ease it with a soft step and a private note."),
        ex("calm-005", "calm", "exhausted burnt out", "Burnout is heavy — slow down and draft a gentle version of the post."),
        ex("calm-006", "calm", "losing my grip", "Grip slipping — ground yourself and take one soft step today."),
        ex("calm-007", "calm", "stacked against me", "Stacked day — breathe, write privately, one tiny step is enough."),
        ex("calm-008", "calm", "need a moment reset", "Reset moment — put the phone down 30 seconds, then one gentle draft."),
        ex("calm-009", "calm", "panicking about post", "Post panic — ease the moment; first line only, then pause."),
        ex("calm-010", "calm", "heavy moment publishing", "Heavy publish moment — soften with a draft, not a deadline."),
        ex("calm-011", "calm", "drained from comments", "Comment drain — step back and write the first line only."),
        ex("calm-012", "calm", "intense overwhelm thread", "Thread overwhelm — ground, private note, one soft step."),
        ex("calm-013", "calm", "step back need pause", "Pause is smart — gentle draft first, decide later."),
        ex("calm-014", "calm", "anxious before posting", "Pre-post anxiety — breathe and post a seed, not the whole essay."),
        ex("calm-015", "calm", "burned out creator", "Creator burnout — ease the moment with one reversible micro-action."),
        ex("calm-016", "calm", "sharp spike of stress", "Stress spike — soften it; one line in a private note."),
        ex("calm-017", "calm", "spiraling comparison", "Comparison spiral — ground and take one soft step in your lane."),
        ex("calm-018", "calm", "moment feels too big", "Big moment — shrink it: first line only, gentle draft."),
        ex("calm-019", "calm", "exhausted from feed", "Feed exhaustion — slow down and bookmark this for tomorrow."),
        ex("calm-020", "calm", "gentle overwhelm wave", "Overwhelm wave — breathe, ease, one soft step forward."),
    ]
    universal = [
        ex("uni-001", "universal", "everything feels weird", "Share a tiny spark — one sentence is enough to start."),
        ex("uni-002", "universal", "something vague and off", "Weird moment — write one sentence and save the seed privately."),
        ex("uni-003", "universal", "idk what to do", "Unclear spike — react with one emoji or write one line."),
        ex("uni-004", "universal", "random rough moment", "Rough moment — share a tiny version of the thought with your circle."),
        ex("uni-005", "universal", "off day online", "Off day — bookmark this and drop a small spark tomorrow."),
        ex("uni-006", "universal", "not sure why upset", "Fuzzy frustration — write one sentence to name the signal."),
        ex("uni-007", "universal", "weird energy today", "Weird energy — save a draft seed and connect with one soft check-in."),
        ex("uni-008", "universal", "stuck on a thought", "Stuck thought — post a seed, not the final version."),
        ex("uni-009", "universal", "odd frustration spike", "Odd spike — share a tiny spark; momentum starts small."),
        ex("uni-010", "universal", "unclear why mad", "Unclear heat — write one line privately, then one micro-action."),
        ex("uni-011", "universal", "fuzzy bad mood", "Bad mood fuzz — react with one emoji or save the idea."),
        ex("uni-012", "universal", "meh day scrolling", "Meh scroll day — bookmark a seed for when energy returns."),
        ex("uni-013", "universal", "urge to post hot take", "Hot-take itch — draft first; share a tiny version, not the blast."),
        ex("uni-014", "universal", "can't name the feeling", "Unnamed feeling — one sentence is enough to start a thread."),
        ex("uni-015", "universal", "low signal day", "Low-signal day — tiny signals matter; write one line."),
        ex("uni-016", "universal", "blank on what to say", "Blank page — post the seed: one sentence, your circle will meet you."),
        ex("uni-017", "universal", "weird tension building", "Tension building — nudge it into a draft, not a dump."),
        ex("uni-018", "universal", "neutral but restless", "Restless neutral — share a small piece and see what resonates."),
        ex("uni-019", "universal", "undecided about posting", "Undecided — save a draft seed; decide after one breath."),
        ex("uni-020", "universal", "small itch to react", "Small react itch — one emoji or one line keeps momentum alive."),
    ]
    all_examples = humorous + direct + strategic + calm + universal
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"example_responses": all_examples}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(all_examples)} examples to {OUT}")


if __name__ == "__main__":
    main()
