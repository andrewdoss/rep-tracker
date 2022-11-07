import functools
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Any, List

import psycopg2
import pytz
from dotenv import load_dotenv
from psycopg2 import sql

import errors

load_dotenv()

BITDOTIO_DB_NAME = os.getenv("BITDOTIO_DB_NAME")
BITDOTIO_USER = os.getenv("BITDOTIO_USER")
BITDOTIO_PASSWORD = os.getenv("BITDOTIO_PASSWORD")
BITDOTIO_HOST = os.getenv("BITDOTIO_HOST")
BITDOTIO_PORT = int(os.getenv("BITDOTIO_PORT"))
APP_NAME = os.getenv("APP_NAME")


def _get_connect_args(dbname: str = BITDOTIO_DB_NAME) -> str:
    return {
        "dbname": dbname,
        "user": BITDOTIO_USER,
        "password": BITDOTIO_PASSWORD,
        "host": BITDOTIO_HOST,
        "port": BITDOTIO_PORT,
        "application_name": APP_NAME,
        "sslmode": "require",  
    }


def bitdotio_cursor(func):
    @functools.wraps(func)
    def wrapper_bitdotio_cursor(*args, **kwargs):
        with psycopg2.connect(**_get_connect_args()) as conn:
            with conn.cursor() as curs:
                kwargs["curs"] = curs
                return func(*args, **kwargs)
    return wrapper_bitdotio_cursor


@bitdotio_cursor
def create_reps(quantity: int, exercise: str, curs: psycopg2.extensions.cursor):
    qs = sql.SQL(
        """
        INSERT INTO reps (quantity, exercise_id)
        VALUES (%s, (SELECT id FROM exercise WHERE name=%s));
        """
    )
    try:
        curs.execute(qs, (quantity, exercise))
    except psycopg2.errors.NotNullViolation as e:
        if 'null value in column "exercise_id"' in e.pgerror:
            raise errors.UnrecognizedExerciseError
        raise errors.ServerError


@bitdotio_cursor
def aggregate_reps(
    start: datetime,
    end: datetime,
    *,  
    curs: psycopg2.extensions.cursor,
    exercise: Optional[str] = None,
    ) -> List[Tuple[Any, ...]]:
    params = [start, end]
    qs = sql.SQL(
        """
        SELECT exercise.name, SUM(quantity)
        FROM reps
        INNER JOIN exercise 
        ON reps.exercise_id = exercise.id
        WHERE date_created >= %s
        AND date_created < %s
        """
    )
    if exercise is not None:
        qs += sql.SQL("AND exercise_id = (SELECT id FROM exercise WHERE name=%s)")
        params.append(exercise)
    qs += sql.SQL("GROUP BY exercise.name")
    curs.execute(qs, params)
    return [row for row in curs]


def get_todays_reps(
    device_timezone: str = "US/Pacific", 
    exercise: Optional[str] = None,
) -> List[Tuple[Any, ...]]:
    start_local = (datetime.now(timezone.utc)
                           .astimezone(pytz.timezone(device_timezone))
                           .replace(hour=0, minute=0, second=0, microsecond=0))
    start = start_local.astimezone(timezone.utc)
    end = start + timedelta(days=1)
    return aggregate_reps(start, end, exercise=exercise)


if __name__ == "__main__":
    print(get_todays_reps())
    print(get_todays_reps(exercise="pushup"))