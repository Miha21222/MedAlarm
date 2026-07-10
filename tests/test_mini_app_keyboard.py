from app.keyboards.inline import open_menu_keyboard


def test_open_menu_keyboard_includes_https_mini_app():
    keyboard = open_menu_keyboard("https://medalarm.example/app")
    first = keyboard.inline_keyboard[0][0]
    assert first.web_app is not None
    assert first.web_app.url == "https://medalarm.example/app"


def test_open_menu_keyboard_skips_insecure_mini_app_url():
    keyboard = open_menu_keyboard("http://localhost:5173")
    assert all(button.web_app is None for row in keyboard.inline_keyboard for button in row)
