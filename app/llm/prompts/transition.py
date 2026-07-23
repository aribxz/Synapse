TRANSITION_PROMPT = """You are writing a brief bridge between two sections of a study guide.

You will see the end of one section and the start of the next.

Write ONE short, natural sentence that connects them. Like you're talking to a friend:
- "Next, let's look at how..."
- "So how do we actually build one of these?"
- "This raises an important question: ..."

Do NOT use:
- "Now that we have established..."
- "Having explored/covered/examined..."
- "Building upon..."
- Any academic or formulaic phrasing

If the two sections use different terminology for the same concept, add on a new line: NOTATION CLASH: "term1" vs "term2"

Output ONLY the transition sentence (and optional notation clash). No commentary.
"""
