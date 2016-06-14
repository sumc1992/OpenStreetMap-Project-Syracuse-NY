CREATE TABLE nodes_tags(
  id INTEGER,
  key TEXT,
  value TEXT,
  type TEXT,
  FOREIGN KEY (id) REFERENCES nodes (id)
);

CREATE TABLE ways_tags(
  id INTEGER,
  key TEXT,
  value TEXT,
  type TEXT,
  FOREIGN KEY (id) REFERENCES ways (id)
);

CREATE TABLE ways_nodes(
  id INTEGER,
  node_id INTEGER,
  position INTEGER,
  FOREIGN KEY (id) REFERENCES ways (id),
  FOREIGN KEY (node_id) REFERENCES nodes (id)
);

CREATE TABLE nodes(
  id INT PRIMARY KEY,
  lat FLOAT,
  lon FLOAT,
  user TEXT,
  uid INTEGER,
  version INTEGER,
  changeset INTEGER,
  timestamp TEXT
);

CREATE TABLE ways(
  id INT PRIMARY KEY,
  user TEXT,
  uid INTEGER,
  version INTEGER,
  changeset INTEGER,
  timestamp TEXT
);
