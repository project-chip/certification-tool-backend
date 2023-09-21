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
import logging
import sys

from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.db.base_class import Base
from app.db.init_db import create_app_database, drop_app_database, init_db
from app.tests.conftest import TestingSessionLocal, test_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def init(reset_db: bool = False) -> None:
    try:
        if reset_db:
            drop_app_database(test_engine)
        create_app_database(test_engine)
        db = TestingSessionLocal()
        Base.metadata.create_all(bind=test_engine)
        init_db(db)
    except Exception as e:
        logger.error(e)
        raise e


def main(reset_db: bool = False) -> None:
    logger.info("Initializing service")
    init(reset_db=reset_db)
    logger.info("Service finished initializing")


if __name__ == "__main__":
    reset_db = "--reset-db" in sys.argv
    main(reset_db=reset_db)
