Coimbatore
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --app-dir /home/$USER/dev/dubai-lms/backend
```sh
mysql -u root -p -D cloudnative_lms
```
```
mysql -u root -p
DROP DATABASE cloudnative_lms;
CREATE DATABASE cloudnative_lms;
GRANT ALL PRIVILEGES ON cloudnative_lms.* TO 'root'@'localhost' IDENTIFIED BY 'a';
FLUSH PRIVILEGES;
use cloudnative_lms;
```


```sql
-- Insert data into the users table
INSERT INTO users (id, username, email, password_hash, user_type, is_active) VALUES
(1, 'admin', 'admin@example.com', '$2b$12$WofojNbsiCmELgmExBz0D.aLla5l3GI9BQwEXjR3FYeBmWxO1O3gO', 'Admin', 1),
(2, 'vedajanani', 'vedajanani@example.com', '$2b$12$uJqKHUEUEYZRkOvFfhLdxOMih5I8XinledLzJFJEoX6zV9VmWgncq', 'Teacher', 1),
(3, 'demostudent', 'demostudent@example.com', '$2b$12$BdIRfOnJ46si.DeCpPlMy.SFd9Nsxf/x39weY1cGk7lbnwQpB9fla', 'Student', 1);

-- Insert data into the grades table
INSERT INTO grades (name) VALUES
    ('5'), ('6'), ('7'), ('8'), ('9');

-- Insert data into the subjects table
INSERT INTO subjects (name, grade_id) VALUES
    ('Mathematics', 1), -- Grade 5
    ('Science', 1),     -- Grade 5
    ('English', 2),     -- Grade 6
    ('History', 2),     -- Grade 6
    ('Art', 3);         -- Grade 7

-- Insert data into the lessons table
INSERT INTO lessons (name, subject_id) VALUES
    ('Introduction to Algebra', 1),       -- Mathematics Grade 5
    ('Basic Geometry Concepts', 1),       -- Mathematics Grade 5
    ('The Solar System', 2),             -- Science Grade 5
    ('Plant Life Cycles', 2),            -- Science Grade 5
    ('Parts of Speech', 3);              -- English Grade 6

-- Insert data into the urls table
-- Insert data into the urls table
INSERT INTO urls (url, urlType) VALUES
    ('https://example.com/algebra_basics_worksheet.pdf', 'https'),       -- url_id: 1 (for pdfs id 1)
    ('https://example.com/geometry_terms_glossary.pdf', 'https'),        -- url_id: 2 (for pdfs id 2)
    ('https://example.com/solar_system_exploration.pdf', 'https'),      -- url_id: 3 (for pdfs id 3)
    ('https://example.com/plant_reproduction_guide.pdf', 'https'),       -- url_id: 4 (for pdfs id 4)
    ('https://example.com/grammar_essentials_handbook.pdf', 'https'),    -- url_id: 5 (for pdfs id 5)
    ('http://example.com/algebraic_expressions_explained.mp4', 'http'), -- url_id: 6 (for videos id 1)
    ('http://example.com/geometric_shapes_demo.avi', 'http'),          -- url_id: 7 (for videos id 2)
    ('http://example.com/interactive_solar_system_tour.mkv', 'http'),    -- url_id: 8 (for videos id 3)
    ('http://example.com/pollination_process_visualization.mov', 'http'), -- url_id: 9 (for videos id 4)
    ('http://example.com/identifying_verbs_tutorial.mp4', 'http'),    -- url_id: 10 (for videos id 5)
    ('gs://my-lms-bucket/equation_example.png', 'gs'),        -- url_id: 11 (for images id 1)
    ('gs://my-lms-bucket/triangle_diagram.jpg', 'gs'),        -- url_id: 12 (for images id 2)
    ('gs://my-lms-bucket/planet_orbit_animation.gif', 'gs'),      -- url_id: 13 (for images id 3)
    ('gs://my-lms-bucket/flower_anatomy_chart.svg', 'gs'),       -- url_id: 14 (for images id 4)
    ('gs://my-lms-bucket/noun_examples_table.png', 'gs');    -- url_id: 15 (for images id 5)

-- Insert data into the pdfs table
INSERT INTO pdfs (name, lesson_id, url_id) VALUES
    ('algebra_basics_worksheet.pdf', 1, 1),          -- Introduction to Algebra
    ('geometry_terms_glossary.pdf', 2, 2),          -- Basic Geometry Concepts
    ('solar_system_exploration.pdf', 3, 3),         -- The Solar System
    ('plant_reproduction_guide.pdf', 4, 4),        -- Plant Life Cycles
    ('grammar_essentials_handbook.pdf', 5, 5);       -- Parts of Speech

-- Insert data into the videos table
INSERT INTO videos (name, lesson_id, url_id) VALUES
    ('algebraic_expressions_explained.mp4', 1, 6),  -- Introduction to Algebra
    ('geometric_shapes_demo.avi', 2, 7),           -- Basic Geometry Concepts
    ('interactive_solar_system_tour.mkv', 3, 8),   -- The Solar System
    ('pollination_process_visualization.mov', 4, 9),  -- Plant Life Cycles
    ('identifying_verbs_tutorial.mp4', 5, 10);      -- Parts of Speech

-- Insert data into the images table
INSERT INTO images (name, pdf_id, image_number, page_number, chapter_number, url_id) VALUES
    ('equation_example.png', 1, 1, 5, 1, 11),     -- algebra_basics_worksheet.pdf
    ('triangle_diagram.jpg', 2, 1, 3, 2, 12),     -- geometry_terms_glossary.pdf
    ('planet_orbit_animation.gif', 3, 1, 10, 1, 13),  -- solar_system_exploration.pdf
    ('flower_anatomy_chart.svg', 4, 1, 2, 1, 14),    -- plant_reproduction_guide.pdf
    ('noun_examples_table.png', 5, 1, 1, 1, 15);    -- grammar_essentials_handbook.pdf
```

-- You can also insert with NULL values for optional columns if needed
-- INSERT INTO images (name, pdf_id) VALUES ('another_image.png', 8);
    
```sql
show tables;
select * from parents;
select * from students;
select * from users;
select * from teachers;
select * from courses;


describe parents;
describe students;
describe teachers;
describe users;
```
databse details
    db: cloudnative_lms
    username : root
    password : a

vmdetails
    ssh bhagavan@34.93.89.114 
    password: a

users details
    admin, Coimbatore

Screens
    Grades & Sections
    Students
    Teachers
    Parents

Table relations foreign keys
+------------+-------------+-----------------+-----------------------+------------------------+
| TABLE_NAME | COLUMN_NAME | CONSTRAINT_NAME | REFERENCED_TABLE_NAME | REFERENCED_COLUMN_NAME |
+------------+-------------+-----------------+-----------------------+------------------------+
| teachers   | user_id     | teachers_ibfk_1 | users                 | id                     |
| parents    | user_id     | parents_ibfk_1  | users                 | id                     |
| students   | user_id     | students_ibfk_1 | users                 | id                     |
+------------+-------------+-----------------+-----------------------+------------------------+


Coimbatore
##########changes
* 1. Sujects based on grade id
* 2. Lessons based on subject id
* 3. PDF of a lesson
* 4. videos of a lesson
* 5. images based on lesson
* 6. images based on pdf

7. Name of the pdf should be pdfs.id i.e. 3.pdf, not 'Chapter_1.pdf' it might get conflict
    MariaDB [cloudnative_lms]> select * from pdfs;
    +----+-----------+-----------+--------+
    | id | name      | lesson_id | url_id |
    +----+-----------+-----------+--------+
    |  3 | Chapter 1 |         1 |      6 |
    +----+-----------+-----------+--------+
    1 row in set (0.001 sec)

    MariaDB [cloudnative_lms]> select * from urls;
    +----+----------------------------------------------------------+---------+
    | id | url                                                      | urlType |
    +----+----------------------------------------------------------+---------+
    |  6 | https://storage.googleapis.com/lms-ai/pdfs/Chapter_1.pdf | pdf     |
    +----+----------------------------------------------------------+---------+

8. Same case with video name in the cloud
9. Same case with video name in the image
10. make urls.urlType should be appropriate like gs, https, basically protocol name
