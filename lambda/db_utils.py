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
def create_reps(
    quantity: int,
    exercise: str,
    hashed_device_id: str,
    curs: psycopg2.extensions.cursor
    ) -> None:
    qs = sql.SQL(
        """
        INSERT INTO reps (device_id, quantity, exercise_id)
        VALUES (%s, %s, (SELECT id FROM exercise WHERE name=%s));
        """
    )
    try:
        curs.execute(qs, (hashed_device_id, quantity, exercise))
    except psycopg2.errors.NotNullViolation as e:
        if 'null value in column "exercise_id"' in e.pgerror:
            raise errors.UnrecognizedExerciseError
        raise errors.ServerError


@bitdotio_cursor
def agg_total_reps(
    start: datetime,
    end: datetime,
    hashed_device_id: str,
    *,  
    curs: psycopg2.extensions.cursor,
    exercise: Optional[str] = None,
    ) -> List[Tuple[Any, ...]]:
    """Sums total reps within specified window."""
    params = [start, end, hashed_device_id]
    qs = sql.SQL(
        """
        SELECT exercise.name, SUM(quantity)
        FROM reps
        INNER JOIN exercise 
        ON reps.exercise_id = exercise.id
        WHERE date_created >= %s
        AND date_created < %s
        AND device_id = %s
        """
    )
    if exercise is not None:
        qs += sql.SQL("AND exercise_id = (SELECT id FROM exercise WHERE name=%s)")
        params.append(exercise)
    qs += sql.SQL("GROUP BY exercise.name")
    curs.execute(qs, params)
    return [row for row in curs]


@bitdotio_cursor
def agg_daily_reps(
    start: datetime,
    end: datetime,
    device_timezone: str,
    hashed_device_id: str,
    *,  
    curs: psycopg2.extensions.cursor,
    exercise: Optional[str] = None,
    ) -> List[Tuple[Any, ...]]:
    """Sums daily reps within specified window."""
    params = [device_timezone, start, end, hashed_device_id]
    qs = sql.SQL(
        """
        SELECT
          date_trunc('day', date_created AT TIME ZONE %s) AS "date",
          exercise.name As "exercise",
          SUM(quantity) AS "value"
        FROM reps
        INNER JOIN exercise 
        ON reps.exercise_id = exercise.id
        WHERE date_created >= %s
        AND date_created < %s
        AND device_id = %s
        """
    )
    if exercise is not None:
        qs += sql.SQL("AND exercise_id = (SELECT id FROM exercise WHERE name=%s)")
        params.append(exercise)
    qs += sql.SQL(
        """
        GROUP BY date, exercise.name
        ORDER BY date
        """
    )
    curs.execute(qs, params)
    return [[d.name for d in curs.description]] + [row for row in curs]


def get_todays_reps(
    hashed_device_id: str,
    device_timezone: str = "US/Pacific", 
    exercise: Optional[str] = None,
) -> List[Tuple[Any, ...]]:
    start_local = (datetime.now(timezone.utc)
                           .astimezone(pytz.timezone(device_timezone))
                           .replace(hour=0, minute=0, second=0, microsecond=0))
    start = start_local.astimezone(timezone.utc)
    end = start + timedelta(days=1)
    return agg_total_reps(start, end, hashed_device_id, exercise=exercise)


def get_daily_reps(
    hashed_device_id: str,
    device_timezone: str = "US/Pacific", 
    exercise: Optional[str] = None,
) -> List[Tuple[Any, ...]]:
    today_local = (datetime.now(timezone.utc)
                           .astimezone(pytz.timezone(device_timezone))
                           .replace(hour=0, minute=0, second=0, microsecond=0))
    today_utc = today_local.astimezone(timezone.utc)
    end_utc = today_utc + timedelta(days=1)
    start_utc = end_utc - timedelta(days=14)
    return agg_daily_reps(
        start_utc,
        end_utc,
        device_timezone,
        hashed_device_id,
        exercise=exercise,
    )


if __name__ == "__main__":
    print(get_todays_reps("cf3408e5a22912f134f5b9376587e106303f2ce817852b055fa0ba1851df512d"))
    print(get_daily_reps("cf3408e5a22912f134f5b9376587e106303f2ce817852b055fa0ba1851df512d"))