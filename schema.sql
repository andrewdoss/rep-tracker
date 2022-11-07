DROP TABLE IF EXISTS goal;
DROP TABLE IF EXISTS reps;
DROP TABLE IF EXISTS goal_interval;
DROP TABLE IF EXISTS exercise;


CREATE TABLE exercise (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE goal_interval (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    name TEXT NOT NULL,
    days INTEGER NOT NULL
);

CREATE TABLE goal (
    id SERIAL PRIMARY KEY,
    quantity INTEGER NOT NULL ,
    goal_interval_id INTEGER NOT NULL REFERENCES goal_interval (id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercise (id) ON DELETE CASCADE
);

CREATE TABLE reps (
    id SERIAL PRIMARY KEY,
    date_created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    quantity INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL REFERENCES exercise (id) ON DELETE CASCADE
);

INSERT INTO exercise (name)
VALUES
  ('pushup'),
  ('pullup'),
  ('squat'),
  ('dip'),
  ('row');

INSERT INTO goal_interval (name, days)
VALUES
  ('daily', 1),
  ('weekly', 7),
  ('monthly', 30);


