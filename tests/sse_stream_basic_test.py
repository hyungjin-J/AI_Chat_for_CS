#!/usr/bin/env python3
"""Basic SSE contract tests for UI-level behavior assumptions."""

from __future__ import annotations

import unittest


class StreamState:
    def __init__(self) -> None:
        self.tokens: list[str] = []
        self.citations: list[dict] = []
        self.done = False
        self.block_send = False
        self.last_event_id: str | None = None
        self.seen_event_ids: set[str] = set()
        self.reconnect_attempts = 0

    def apply(self, event_id: str, event_type: str, payload: dict) -> None:
        if event_id in self.seen_event_ids:
            return
        self.seen_event_ids.add(event_id)
        self.last_event_id = event_id

        if event_type == 'token':
            self.tokens.append(payload.get('text', ''))
        elif event_type == 'citation':
            self.citations.append(payload)
        elif event_type == 'safe_response':
            self.block_send = True
        elif event_type == 'done':
            self.done = True

    def reconnect(self) -> bool:
        self.reconnect_attempts += 1
        return self.reconnect_attempts <= 3

    def finalize(self) -> None:
        if self.done and not self.citations:
            self.block_send = True


class TestSseStreamBasic(unittest.TestCase):
    def test_token_citation_done_order(self) -> None:
        state = StreamState()
        events = [
            ('1', 'token', {'text': '안'}),
            ('2', 'token', {'text': '녕하세요'}),
            ('3', 'citation', {'doc_id': 'kb-1', 'rank': 1}),
            ('4', 'done', {}),
        ]
        for event in events:
            state.apply(*event)
        state.finalize()

        self.assertEqual(''.join(state.tokens), '안녕하세요')
        self.assertEqual(len(state.citations), 1)
        self.assertTrue(state.done)
        self.assertFalse(state.block_send)

    def test_resume_after_disconnect_and_duplicate_chunk_ignored(self) -> None:
        state = StreamState()

        state.apply('1', 'token', {'text': '응답 '})
        state.apply('2', 'token', {'text': '초안'})

        self.assertTrue(state.reconnect())
        resumed_events = [
            ('2', 'token', {'text': '초안'}),
            ('3', 'citation', {'doc_id': 'kb-2', 'rank': 1}),
            ('4', 'done', {}),
        ]
        for event in resumed_events:
            state.apply(*event)
        state.finalize()

        self.assertEqual(''.join(state.tokens), '응답 초안')
        self.assertEqual(len(state.citations), 1)
        self.assertFalse(state.block_send)

    def test_reconnect_attempt_limit(self) -> None:
        state = StreamState()
        self.assertTrue(state.reconnect())
        self.assertTrue(state.reconnect())
        self.assertTrue(state.reconnect())
        self.assertFalse(state.reconnect())

    def test_missing_citation_fail_closed(self) -> None:
        state = StreamState()
        state.apply('10', 'token', {'text': '근거 없는 답변'})
        state.apply('11', 'done', {})
        state.finalize()

        self.assertTrue(state.done)
        self.assertTrue(state.block_send)

    def test_safe_response_event_blocks_send(self) -> None:
        state = StreamState()
        state.apply('20', 'safe_response', {'reason': 'policy'})
        state.apply('21', 'done', {})
        state.finalize()
        self.assertTrue(state.block_send)


if __name__ == '__main__':
    unittest.main()
