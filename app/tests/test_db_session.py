#
# Copyright (c) 2023 Project CHIP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from typing import Iterator
from unittest import mock

from sqlalchemy.orm import Session

from app.db.session import iter_with_session


def test_iter_with_session_opens_session_lazily_and_closes_it_when_done() -> None:
    session = mock.MagicMock()
    with mock.patch("app.db.session.SessionLocal", return_value=session) as factory:
        items = iter_with_session(lambda db: iter([db]))
        factory.assert_not_called()

        assert list(items) == [session]
        session.close.assert_called_once()


def test_iter_with_session_closes_session_when_closed_early() -> None:
    def produce(db: Session) -> Iterator[int]:
        yield 1
        yield 2

    session = mock.MagicMock()
    with mock.patch("app.db.session.SessionLocal", return_value=session):
        items = iter_with_session(produce)
        assert next(items) == 1
        session.close.assert_not_called()

        items.close()
        session.close.assert_called_once()
