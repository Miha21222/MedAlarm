from app.keyboards.inline import open_mini_app_keyboard


def test_open_mini_app_keyboard_includes_only_https_mini_app():
    keyboard = open_mini_app_keyboard("https://medalarm.example/app")

    assert len(keyboard.inline_keyboard) == 1
    button = keyboard.inline_keyboard[0][0]
    assert button.web_app is not None
    assert button.web_app.url == "https://medalarm.example/app?app_version=account-sync-v2"
    assert button.callback_data is None


def test_open_mini_app_keyboard_skips_insecure_mini_app_url():
    keyboard = open_mini_app_keyboard("http://localhost:5173")

    assert keyboard.inline_keyboard == []
