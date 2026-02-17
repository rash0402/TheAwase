"""UIButtonクラスのテスト"""
import pygame
pygame.init()

from theawase.ui.button import UIButton


def _click_event(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': pos, 'button': 1})


def _release_event(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': pos, 'button': 1})


def test_button_click_inside():
    """ボタン内クリックでon_clickが呼ばれる"""
    clicked = []
    btn = UIButton(pygame.Rect(100, 100, 200, 50), "テスト", lambda: clicked.append(True))
    btn.handle_event(_click_event((150, 125)))
    btn.handle_event(_release_event((150, 125)))
    assert clicked == [True]


def test_button_click_outside():
    """ボタン外クリックでon_clickが呼ばれない"""
    clicked = []
    btn = UIButton(pygame.Rect(100, 100, 200, 50), "テスト", lambda: clicked.append(True))
    btn.handle_event(_click_event((50, 50)))
    btn.handle_event(_release_event((50, 50)))
    assert clicked == []


def test_button_selected_state():
    """selectedプロパティが正しく動作する"""
    btn = UIButton(pygame.Rect(0, 0, 100, 40), "test", lambda: None)
    assert btn.selected is False
    btn.selected = True
    assert btn.selected is True


def test_button_returns_true_on_click():
    """クリック確定時にhandle_eventがTrueを返す"""
    btn = UIButton(pygame.Rect(0, 0, 100, 40), "test", lambda: None)
    btn.handle_event(_click_event((50, 20)))
    result = btn.handle_event(_release_event((50, 20)))
    assert result is True


def test_button_returns_false_on_click_outside():
    """外側クリックはFalseを返す"""
    btn = UIButton(pygame.Rect(0, 0, 100, 40), "test", lambda: None)
    btn.handle_event(_click_event((200, 200)))
    result = btn.handle_event(_release_event((200, 200)))
    assert result is False
