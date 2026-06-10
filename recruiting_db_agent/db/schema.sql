-- =============================================================
-- db/schema.sql
-- Recruiting MAS Database — DDL + Seed Data
-- =============================================================

USE recruiting_mas;

-- -----------------------------------------------------------
-- TABLE: candidates
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidates (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    email       VARCHAR(180) UNIQUE,
    phone       VARCHAR(20),
    role        VARCHAR(100),
    skills      TEXT,
    status      ENUM(
                  'applied','screening',
                  'interview','hired','rejected'
                ) DEFAULT 'applied',
    experience  FLOAT DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- TABLE: jobs
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    title        VARCHAR(120) NOT NULL,
    department   VARCHAR(80),
    required_exp FLOAT DEFAULT 0,
    skills       TEXT,
    open_slots   INT DEFAULT 1,
    status       ENUM('open','closed','on_hold') DEFAULT 'open',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------
-- TABLE: call_logs
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS call_logs (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    recruiter    VARCHAR(100) DEFAULT 'System',
    call_type    ENUM(
                   'screening','interview_schedule',
                   'offer','follow_up'
                 ) NOT NULL,
    scheduled_at DATETIME,
    status       ENUM(
                   'pending','completed',
                   'no_answer','rescheduled'
                 ) DEFAULT 'pending',
    notes        TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

-- =============================================================
-- SEED: Named candidates (6)
-- =============================================================
INSERT INTO candidates (name, email, phone, role, skills, status, experience) VALUES
('Priya Sharma',  'priya@email.com',  '+91-9876543210', 'Backend Developer',    'Python,Django,MySQL',        'applied',   3.5),
('Rahul Verma',   'rahul@email.com',  '+91-9123456780', 'Frontend Developer',   'React,TypeScript,Vue',       'screening', 2.0),
('Anita Rao',     'anita@email.com',  '+91-9988776655', 'Data Scientist',       'Python,ML,TensorFlow',       'interview', 4.0),
('Kiran Patel',   'kiran@email.com',  '+91-9001122334', 'Full Stack Developer', 'Python,React,MySQL',         'applied',   1.5),
('Suresh Kumar',  'suresh@email.com', '+91-9876501234', 'DevOps Engineer',      'Docker,Kubernetes,AWS',      'applied',   3.0),
('Deepak Singh',  'deepak@email.com', '+91-9111222333', 'Data Scientist',       'Python,R,SQL,Tableau',       'applied',   5.0);

-- =============================================================
-- SEED: 100 dummy candidates
-- =============================================================
INSERT INTO candidates (name, email, phone, role, skills, status, experience) VALUES
('Amit Gupta',       'amit.gupta@email.com',       '+91-9000000101', 'Backend Developer',    'Java,Spring,MySQL',             'applied',   2.5),
('Sneha Nair',       'sneha.nair@email.com',        '+91-9000000102', 'Frontend Developer',   'HTML,CSS,JavaScript',           'screening', 1.0),
('Vikram Reddy',     'vikram.reddy@email.com',      '+91-9000000103', 'Data Scientist',       'Python,Pandas,Scikit-learn',    'applied',   3.0),
('Pooja Mehta',      'pooja.mehta@email.com',       '+91-9000000104', 'Full Stack Developer', 'Node.js,React,MongoDB',         'interview', 4.5),
('Arjun Iyer',       'arjun.iyer@email.com',        '+91-9000000105', 'DevOps Engineer',      'Jenkins,Terraform,Azure',       'applied',   2.0),
('Kavita Joshi',     'kavita.joshi@email.com',      '+91-9000000106', 'Backend Developer',    'Python,FastAPI,PostgreSQL',     'hired',     5.0),
('Rohit Shukla',     'rohit.shukla@email.com',      '+91-9000000107', 'Frontend Developer',   'React,Next.js,Tailwind',        'screening', 2.5),
('Divya Menon',      'divya.menon@email.com',       '+91-9000000108', 'Data Scientist',       'R,ggplot2,Tableau',             'applied',   1.5),
('Sandeep Pillai',   'sandeep.pillai@email.com',    '+91-9000000109', 'Full Stack Developer', 'Django,Vue,MySQL',              'applied',   3.5),
('Meera Krishnan',   'meera.krishnan@email.com',    '+91-9000000110', 'DevOps Engineer',      'Kubernetes,Helm,GCP',           'screening', 4.0),
('Tarun Bose',       'tarun.bose@email.com',        '+91-9000000111', 'Backend Developer',    'Go,gRPC,Redis',                 'applied',   2.0),
('Nisha Agarwal',    'nisha.agarwal@email.com',     '+91-9000000112', 'Frontend Developer',   'Angular,TypeScript,SCSS',       'interview', 3.0),
('Praveen Rao',      'praveen.rao@email.com',       '+91-9000000113', 'Data Scientist',       'Python,NLP,BERT',               'applied',   5.5),
('Swati Verma',      'swati.verma@email.com',       '+91-9000000114', 'Full Stack Developer', 'Rails,React,PostgreSQL',        'applied',   2.5),
('Karthik Nair',     'karthik.nair@email.com',      '+91-9000000115', 'DevOps Engineer',      'Docker,Ansible,AWS',            'hired',     6.0),
('Prathap Chandra',  'prathap.chandra@email.com',   '+91-9000000116', 'Backend Developer',    'Kotlin,Spring Boot,Kafka',      'screening', 3.0),
('Lakshmi Devi',     'lakshmi.devi@email.com',      '+91-9000000117', 'Frontend Developer',   'Svelte,JavaScript,GraphQL',     'applied',   1.0),
('Naveen Kumar',     'naveen.kumar@email.com',       '+91-9000000118', 'Data Scientist',       'Python,XGBoost,Feature Eng',    'applied',   2.0),
('Radha Krishnan',   'radha.krishnan@email.com',    '+91-9000000119', 'Full Stack Developer', 'Flask,Bootstrap,SQLite',        'interview', 3.5),
('Sunil Yadav',      'sunil.yadav@email.com',       '+91-9000000120', 'DevOps Engineer',      'CircleCI,Terraform,AWS',        'applied',   1.5),
('Arun Saxena',      'arun.saxena@email.com',       '+91-9000000121', 'Backend Developer',    'PHP,Laravel,MySQL',             'rejected',  1.0),
('Preethi Subbu',    'preethi.subbu@email.com',     '+91-9000000122', 'Frontend Developer',   'React,Redux,Jest',              'applied',   2.0),
('Gaurav Tiwari',    'gaurav.tiwari@email.com',     '+91-9000000123', 'Data Scientist',       'Python,OpenCV,Deep Learning',   'screening', 4.0),
('Bhavana Iyer',     'bhavana.iyer@email.com',      '+91-9000000124', 'Full Stack Developer', 'MEAN Stack,GraphQL',            'applied',   3.0),
('Dinesh Prabhu',    'dinesh.prabhu@email.com',     '+91-9000000125', 'DevOps Engineer',      'Spinnaker,Prometheus,Grafana',  'applied',   2.5),
('Hema Latha',       'hema.latha@email.com',        '+91-9000000126', 'Backend Developer',    'Rust,WebAssembly,PostgreSQL',   'applied',   1.5),
('Manoj Pillai',     'manoj.pillai@email.com',      '+91-9000000127', 'Frontend Developer',   'Vue,Vuex,Nuxt.js',              'interview', 3.5),
('Rekha Nambiar',    'rekha.nambiar@email.com',     '+91-9000000128', 'Data Scientist',       'SAS,SPSS,Python',               'applied',   6.0),
('Sajith Kumar',     'sajith.kumar@email.com',       '+91-9000000129', 'Full Stack Developer', 'Node.js,MongoDB,Express',       'screening', 2.0),
('Tanya Sharma',     'tanya.sharma@email.com',      '+91-9000000130', 'DevOps Engineer',      'GitHub Actions,Docker,K8s',     'applied',   1.0),
('Vivek Anand',      'vivek.anand@email.com',       '+91-9000000131', 'Backend Developer',    'C#,.NET,Azure SQL',             'applied',   4.0),
('Yamini Reddy',     'yamini.reddy@email.com',      '+91-9000000132', 'Frontend Developer',   'React Native,Expo,Firebase',    'applied',   2.5),
('Ashwin Babu',      'ashwin.babu@email.com',       '+91-9000000133', 'Data Scientist',       'Python,Spark,Hadoop',           'interview', 5.0),
('Chitra Rajan',     'chitra.rajan@email.com',      '+91-9000000134', 'Full Stack Developer', 'Django,React,Redis',            'applied',   3.0),
('Farhan Siddiqui',  'farhan.siddiqui@email.com',   '+91-9000000135', 'DevOps Engineer',      'Puppet,Chef,AWS OpsWorks',      'screening', 4.5),
('Geetha Kumari',    'geetha.kumari@email.com',     '+91-9000000136', 'Backend Developer',    'Node.js,TypeScript,DynamoDB',   'applied',   1.0),
('Hari Prasad',      'hari.prasad@email.com',       '+91-9000000137', 'Frontend Developer',   'Ember.js,Handlebars,SASS',      'rejected',  0.5),
('Indira Gandhi S',  'indira.s@email.com',          '+91-9000000138', 'Data Scientist',       'Julia,Statistics,Data Viz',     'applied',   3.5),
('Jaya Prakash',     'jaya.prakash@email.com',      '+91-9000000139', 'Full Stack Developer', 'Laravel,Vue,MySQL',             'applied',   2.0),
('Kala Sundar',      'kala.sundar@email.com',       '+91-9000000140', 'DevOps Engineer',      'Rancher,Fleet,Longhorn',        'hired',     5.5),
('Lenin Raj',        'lenin.raj@email.com',         '+91-9000000141', 'Backend Developer',    'Scala,Akka,Cassandra',          'screening', 3.0),
('Mala Devi',        'mala.devi@email.com',         '+91-9000000142', 'Frontend Developer',   'React,Storybook,Cypress',       'applied',   2.5),
('Nagaraj S',        'nagaraj.s@email.com',         '+91-9000000143', 'Data Scientist',       'Python,Keras,Computer Vision',  'applied',   4.0),
('Oviya Priya',      'oviya.priya@email.com',       '+91-9000000144', 'Full Stack Developer', 'FastAPI,React,Postgres',        'interview', 3.5),
('Prabhu Doss',      'prabhu.doss@email.com',       '+91-9000000145', 'DevOps Engineer',      'Argo CD,Flux,Tekton',           'applied',   2.0),
('Queen Selvi',      'queen.selvi@email.com',       '+91-9000000146', 'Backend Developer',    'Ruby,Rails,Sidekiq',            'applied',   1.5),
('Raja Gopal',       'raja.gopal@email.com',        '+91-9000000147', 'Frontend Developer',   'Backbone.js,jQuery,Bootstrap',  'applied',   0.5),
('Sakthi Vel',       'sakthi.vel@email.com',        '+91-9000000148', 'Data Scientist',       'Python,AutoML,H2O',             'screening', 3.0),
('Thilaga Vathi',    'thilaga.vathi@email.com',     '+91-9000000149', 'Full Stack Developer', 'Spring Boot,Angular,Oracle',    'applied',   5.0),
('Uma Maheswari',    'uma.maheswari@email.com',     '+91-9000000150', 'DevOps Engineer',      'Vagrant,VirtualBox,Bash',       'applied',   1.0),
('Valli Azhagan',    'valli.azhagan@email.com',     '+91-9000000151', 'Backend Developer',    'Python,Celery,RabbitMQ',        'applied',   2.5),
('Waris Khan',       'waris.khan@email.com',        '+91-9000000152', 'Frontend Developer',   'React,PWA,Service Worker',      'interview', 3.5),
('Xavier Raj',       'xavier.raj@email.com',        '+91-9000000153', 'Data Scientist',       'Python,Dask,Arrow',             'applied',   4.5),
('Yovan Raj',        'yovan.raj@email.com',         '+91-9000000154', 'Full Stack Developer', 'Meteor,React,MongoDB',          'applied',   1.5),
('Zara Begum',       'zara.begum@email.com',        '+91-9000000155', 'DevOps Engineer',      'Docker Swarm,Consul,Vault',     'screening', 3.0),
('Abhinav Mishra',   'abhinav.mishra@email.com',    '+91-9000000156', 'Backend Developer',    'Elixir,Phoenix,Postgres',       'applied',   2.0),
('Bhavani Shan',     'bhavani.shan@email.com',      '+91-9000000157', 'Frontend Developer',   'React,Material-UI,Redux',       'applied',   4.0),
('Chetan Pandit',    'chetan.pandit@email.com',     '+91-9000000158', 'Data Scientist',       'Python,NLTK,spaCy',             'hired',     6.0),
('Dhruv Kapoor',     'dhruv.kapoor@email.com',      '+91-9000000159', 'Full Stack Developer', 'Nest.js,React,TypeScript',      'applied',   3.0),
('Ezhil Arasu',      'ezhil.arasu@email.com',       '+91-9000000160', 'DevOps Engineer',      'Istio,Envoy,Linkerd',           'applied',   2.5),
('Fathima Begum',    'fathima.begum@email.com',     '+91-9000000161', 'Backend Developer',    'Python,Django REST,JWT',        'screening', 1.5),
('Girish Nair',      'girish.nair@email.com',       '+91-9000000162', 'Frontend Developer',   'Vue3,Pinia,Vite',               'applied',   2.0),
('Hari Krishnan',    'hari.krishnan@email.com',     '+91-9000000163', 'Data Scientist',       'Python,Statsmodels,Scipy',      'interview', 3.5),
('Iswarya Devi',     'iswarya.devi@email.com',      '+91-9000000164', 'Full Stack Developer', 'Golang,React,Postgres',         'applied',   4.0),
('Jagadish Babu',    'jagadish.babu@email.com',     '+91-9000000165', 'DevOps Engineer',      'SonarQube,Nexus,Jenkins',       'applied',   1.0),
('Kamala Devi',      'kamala.devi@email.com',       '+91-9000000166', 'Backend Developer',    'Java,Hibernate,Oracle',         'applied',   5.0),
('Logesh Kumar',     'logesh.kumar@email.com',      '+91-9000000167', 'Frontend Developer',   'React,GraphQL,Apollo',          'rejected',  1.5),
('Murugan Raj',      'murugan.raj@email.com',       '+91-9000000168', 'Data Scientist',       'Python,Prophet,Time Series',    'applied',   3.0),
('Nivetha Thomas',   'nivetha.thomas@email.com',    '+91-9000000169', 'Full Stack Developer', 'Ruby on Rails,React,AWS',       'screening', 4.5),
('Omprakash Rao',    'omprakash.rao@email.com',     '+91-9000000170', 'DevOps Engineer',      'CloudFormation,CDK,Lambda',     'applied',   2.0),
('Padmini Rajan',    'padmini.rajan@email.com',     '+91-9000000171', 'Backend Developer',    'Node.js,GraphQL,Neo4j',         'applied',   3.5),
('Qureshi Ahmed',    'qureshi.ahmed@email.com',     '+91-9000000172', 'Frontend Developer',   'React,Three.js,WebGL',          'interview', 5.0),
('Rajasekaran M',    'rajasekaran.m@email.com',     '+91-9000000173', 'Data Scientist',       'Python,Reinforcement Learning', 'applied',   2.5),
('Saravanan P',      'saravanan.p@email.com',       '+91-9000000174', 'Full Stack Developer', 'PHP,Symfony,Vue',               'applied',   1.0),
('Tamil Selvan',     'tamil.selvan@email.com',      '+91-9000000175', 'DevOps Engineer',      'Packer,Vagrant,Ansible',        'applied',   3.0),
('Usha Rani',        'usha.rani@email.com',         '+91-9000000176', 'Backend Developer',    'Python,Tornado,Elasticsearch',  'screening', 2.0),
('Vasanthi Raj',     'vasanthi.raj@email.com',      '+91-9000000177', 'Frontend Developer',   'React,Emotion,Zustand',         'applied',   4.0),
('Wilson David',     'wilson.david@email.com',      '+91-9000000178', 'Data Scientist',       'Python,Causal Inference,DAGs',  'applied',   3.5),
('Xena Priya',       'xena.priya@email.com',        '+91-9000000179', 'Full Stack Developer', 'Remix,React,Cloudflare',        'hired',     5.5),
('Yogesh Babu',      'yogesh.babu@email.com',       '+91-9000000180', 'DevOps Engineer',      'Crossplane,Backstage,Port',     'applied',   1.5),
('Zeena Begum',      'zeena.begum@email.com',       '+91-9000000181', 'Backend Developer',    'Python,Faststream,Kafka',       'applied',   2.5),
('Aakash Dubey',     'aakash.dubey@email.com',      '+91-9000000182', 'Frontend Developer',   'Solid.js,Qwik,Astro',           'screening', 3.0),
('Babita Roy',       'babita.roy@email.com',        '+91-9000000183', 'Data Scientist',       'Python,LightGBM,CatBoost',      'applied',   4.5),
('Chandru Vel',      'chandru.vel@email.com',       '+91-9000000184', 'Full Stack Developer', 'Hapi.js,Handlebars,MySQL',      'applied',   1.0),
('Dhanushya R',      'dhanushya.r@email.com',       '+91-9000000185', 'DevOps Engineer',      'Datadog,New Relic,Splunk',      'interview', 3.0),
('Elango Mani',      'elango.mani@email.com',       '+91-9000000186', 'Backend Developer',    'Clojure,Datomic,ClojureScript', 'applied',   2.0),
('Feni Balasubram',  'feni.bala@email.com',         '+91-9000000187', 'Frontend Developer',   'React,Tanstack Query,Zod',      'applied',   5.0),
('Govindaraj S',     'govindaraj.s@email.com',      '+91-9000000188', 'Data Scientist',       'Python,Evidently,MLflow',       'applied',   3.5),
('Haritha Priya',    'haritha.priya@email.com',     '+91-9000000189', 'Full Stack Developer', 'Bun.js,Hono,SQLite',            'screening', 2.5),
('Ibrahim Khan',     'ibrahim.khan@email.com',      '+91-9000000190', 'DevOps Engineer',      'OpenTelemetry,Jaeger,Zipkin',   'applied',   1.5),
('Janani Priya',     'janani.priya@email.com',      '+91-9000000191', 'Backend Developer',    'Python,LangChain,ChromaDB',     'applied',   4.0),
('Kalaiarasi T',     'kalaiarasi.t@email.com',      '+91-9000000192', 'Frontend Developer',   'React,Framer Motion,GSAP',      'interview', 3.0),
('Loganathan K',     'loganathan.k@email.com',      '+91-9000000193', 'Data Scientist',       'Python,Polars,DuckDB',          'applied',   5.5),
('Manohari Devi',    'manohari.devi@email.com',     '+91-9000000194', 'Full Stack Developer', 'Supabase,Next.js,Prisma',       'hired',     4.0),
('Natarajan P',      'natarajan.p@email.com',       '+91-9000000195', 'DevOps Engineer',      'Cilium,eBPF,Falco',             'applied',   2.5),
('Oviya Selvi',      'oviya.selvi@email.com',       '+91-9000000196', 'Backend Developer',    'Dart,Flutter,Firebase',         'applied',   1.0),
('Pandian Raj',      'pandian.raj@email.com',       '+91-9000000197', 'Frontend Developer',   'React,Zustand,React Query',     'screening', 3.5),
('Raji Krishnan',    'raji.krishnan@email.com',     '+91-9000000198', 'Data Scientist',       'Python,Vertex AI,BigQuery',     'applied',   6.0),
('Selvi Priya',      'selvi.priya@email.com',       '+91-9000000199', 'Full Stack Developer', 'Convex,React,TypeScript',       'applied',   2.0),
('Thiru Kumar',      'thiru.kumar@email.com',       '+91-9000000200', 'DevOps Engineer',      'Wasm,WASI,Spin Framework',      'applied',   1.5);

-- =============================================================
-- SEED: Jobs
-- =============================================================
INSERT INTO jobs (title, department, required_exp, skills, open_slots, status) VALUES
('Backend Developer',    'Engineering', 2.0, 'Python,Java,MySQL',         3, 'open'),
('Frontend Developer',   'Engineering', 1.5, 'React,TypeScript,CSS',      2, 'open'),
('Data Scientist',       'Analytics',   3.0, 'Python,ML,SQL',             2, 'open'),
('Full Stack Developer', 'Engineering', 2.5, 'Python,React,MySQL',        4, 'open'),
('DevOps Engineer',      'Operations',  3.0, 'Docker,Kubernetes,AWS',     2, 'open'),
('ML Engineer',          'AI/ML',       4.0, 'Python,TensorFlow,PyTorch', 1, 'open');
