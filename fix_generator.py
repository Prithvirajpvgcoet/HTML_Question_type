import re

with open('backend/services/assertion_service/generator.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix max assertions prompt
text = text.replace('Generate EXACTLY 6 assertions. If there are more than 6 testable requirements, combine related checks', 'Generate exactly one assertion per checklist item from step 1. Do not combine unrelated checks to hit a count, and do not fabricate checks to pad it. Minimum 4, maximum 10 total.')

# Replace function signature and internal context building
old_sig = '''async def generate_assertions_from_llm(
    title: str,
    description: str,
    html: str,
    css: str,
    js: str,
) -> list[dict]:'''

new_sig = '''async def generate_assertions_from_llm(
    title: str,
    description: str,
    html: str,
    css: str,
    js: str,
    keep_assertions: list[dict] | None = None,
    failed_context: list[dict] | None = None,
    target_count: int | None = None,
    mode: str = "full"
) -> list[dict]:'''

text = text.replace(old_sig, new_sig)

old_user_msg = '''    user_message = f"""
    Title: {title}
    Description: {description}
    Reference HTML: {html}
    Reference CSS: {css}
    Reference JS: {js}
    """'''

new_user_msg = '''    context_block = ""
    if keep_assertions:
        formatted = "\\n".join(
            f"- {a['trigger']} {a.get('trigger_selector','')} -> {a['check_type']} "
            f"{a.get('check_selector','')} expects {a.get('expected_result','')}"
            for a in keep_assertions
        )
        context_block += (
            f"\\nThe following {len(keep_assertions)} assertions ALREADY PASS validation "
            f"and are FINAL. Do not repeat, rephrase, or overlap their coverage:\\n{formatted}\\n"
        )

    if mode == "diversify" and target_count:
        need = target_count - len(keep_assertions or [])
        context_block += (
            f"\\nGenerate exactly {need} NEW assertions covering DIFFERENT testable "
            f"requirements from the description, not covered above."
        )
    elif mode == "repair" and failed_context:
        formatted_fail = "\\n".join(
            f"- {a['trigger']} {a.get('trigger_selector','')} -> {a['check_type']} "
            f"{a.get('check_selector','')} expected {a.get('expected_result','')}, "
            f"failed because: {a.get('error','')}"
            for a in failed_context
        )
        context_block += (
            f"\\nThe following assertions FAILED against the reference solution. Fix them "
            f"to correctly test the SAME requirement - do not change what already passes:\\n"
            f"{formatted_fail}"
        )

    user_message = f"""
    Title: {title}
    Description: {description}
    Reference HTML: {html}
    Reference CSS: {css}
    Reference JS: {js}
    {context_block}
    """'''

text = text.replace(old_user_msg, new_user_msg)

old_return = '''    # Hard stop at exactly 6 to ensure we always meet the contract,
    # though the prompt structure strongly encourages exactly 6.
    return dict_list[:6]'''

new_return = '''    MAX_ASSERTIONS = 10
    return dict_list[:MAX_ASSERTIONS]'''
text = text.replace(old_return, new_return)

with open('backend/services/assertion_service/generator.py', 'w', encoding='utf-8') as f:
    f.write(text)
