from nodriver import *
import asyncio


async def click_element(element: Element) -> None:
    """Make sure we scroll until el is visible, then hover it and for last it will click it"""
    try:
        await element.scroll_into_view()
        await element.mouse_move()
        await element.click()
    except:
        try:
            await element.click()
        except:
            await element.apply('(el) => el.click()')


async def write_input(value: str, input_elment: Element) -> None:
    """Make sure input is first cleared, then type the value and for last updates it"""
    await input_elment.clear_input()
    await input_elment.send_keys(value)
    await input_elment.update()
    # some times input html value isn't updated
