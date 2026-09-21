ALTER TABLE display
    ADD COLUMN camera_id integer NOT NULL REFERENCES camera(id) ON DELETE CASCADE;

ALTER TABLE display
    ADD CONSTRAINT display_user_camera_date_unique UNIQUE (user_id, camera_id, date);
