INSERT INTO roles (code, name) VALUES
  ('SUPER_ADMIN', 'Platform Administrator'),
  ('COE', 'Controller of Examinations'),
  ('TC', 'Tabulation Committee'),
  ('SCRUTINIZER', 'Scrutinizer'),
  ('DATA_ENTRY', 'Data Entry'),
  ('FACULTY', 'Faculty'),
  ('STUDENT', 'Student')
ON CONFLICT (code) DO NOTHING;
