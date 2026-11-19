PROMPT = """\
Extract only the {garment} worn by the person in the reference photograph.

Create a realistic e-commerce product image.

Requirements:
- Show the garment alone.
- Remove the person completely.
- Remove the face, hands, and body.
- Remove the background.
- Use a plain white background.
- Preserve the garment's original color.
- Preserve fabric texture and stitching.
- Preserve visible logos and design details.
- Do not invent branding.
- Use a front-facing product view.
- Do not include a mannequin or hanger.
"""


def build_prompt(garment: str, instruction: str) -> str:
    prompt = PROMPT.format(garment=garment)
    instruction = instruction.strip()
    if instruction:
        prompt += f"\nAdditional instructions:\n{instruction}\n"
    return prompt


