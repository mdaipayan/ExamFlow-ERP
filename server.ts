import express from "express";
import cors from "cors";
import path from "path";
import { createServer as createViteServer } from "vite";

interface Institution {
  id: string;
  name: string;
  code: string;
  timezone: string;
}

interface User {
  id: string;
  institution_id: string;
  email: string;
  full_name: string;
  roles: string[];
}

interface Programme {
  id: string;
  institution_id: string;
  code: string;
  name: string;
  level: string;
  duration_semesters: number;
}

interface Course {
  id: string;
  institution_id: string;
  code: string;
  name: string;
  credits: number;
  course_type: string;
  is_audit: boolean;
}

interface Regulation {
  id: string;
  institution_id: string;
  name: string;
  code: string;
}

// In-memory data stores for ExamFlow
const institutions: Institution[] = [
  {
    id: "inst-001",
    name: "National Institute of Technology",
    code: "NIT-MAIN",
    timezone: "UTC",
  },
];

const users: User[] = [
  {
    id: "usr-001",
    institution_id: "inst-001",
    email: "admin@examflow.local",
    full_name: "Demo COE Administrator",
    roles: ["SUPER_ADMIN", "COE"],
  },
];

const programmes: Programme[] = [
  {
    id: "prog-001",
    institution_id: "inst-001",
    code: "BTECH-CSE",
    name: "Bachelor of Technology in Computer Science",
    level: "UG",
    duration_semesters: 8,
  },
];

const courses: Course[] = [
  {
    id: "crs-001",
    institution_id: "inst-001",
    code: "CS201",
    name: "Data Structures and Algorithms",
    credits: 4,
    course_type: "THEORY",
    is_audit: false,
  },
];

const regulations: Regulation[] = [
  {
    id: "reg-001",
    institution_id: "inst-001",
    name: "Curriculum Regulation 2024",
    code: "R24",
  },
];

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(cors());
  app.use(express.json());

  // Health check endpoint (parity with backend/app/main.py)
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok", service: "examflow-api" });
  });

  // Setup routes
  app.get("/api/setup/status", (req, res) => {
    res.json({ initialized: users.length > 0 });
  });

  app.post("/api/setup/initialize", (req, res) => {
    const { institution_name, institution_code, admin_name, admin_email } = req.body || {};
    const newInst: Institution = {
      id: `inst-${Date.now()}`,
      name: institution_name || "ExamFlow Institution",
      code: institution_code || "INST",
      timezone: "UTC",
    };
    institutions.push(newInst);

    const newUser: User = {
      id: `usr-${Date.now()}`,
      institution_id: newInst.id,
      email: admin_email || "admin@examflow.local",
      full_name: admin_name || "Administrator",
      roles: ["SUPER_ADMIN", "COE"],
    };
    users.push(newUser);

    res.status(201).json({
      institution_id: newInst.id,
      admin_user_id: newUser.id,
      message: "ExamFlow has been initialized. Create separate operational users next.",
    });
  });

  // Auth routes
  app.post("/api/auth/login", (req, res) => {
    const { email } = req.body || {};
    const foundUser = users.find(
      (u) => u.email.toLowerCase() === (email || "").toLowerCase()
    ) || users[0];

    res.json({
      access_token: `mock_jwt_token_${foundUser.id}`,
      user: {
        id: foundUser.id,
        email: foundUser.email,
        full_name: foundUser.full_name,
        institution_id: foundUser.institution_id,
        roles: foundUser.roles,
      },
    });
  });

  app.get("/api/auth/me", (req, res) => {
    const defaultUser = users[0] || {
      id: "demo",
      email: "demo@examflow.local",
      full_name: "Demo User",
      roles: ["COE"],
    };
    res.json(defaultUser);
  });

  // Academic routes
  app.get("/api/academic/institution", (req, res) => {
    res.json(institutions[0] || { id: "default", name: "ExamFlow", code: "EF" });
  });

  app.get("/api/academic/programmes", (req, res) => {
    res.json(programmes);
  });

  app.post("/api/academic/programmes", (req, res) => {
    const prog: Programme = {
      id: `prog-${Date.now()}`,
      institution_id: institutions[0]?.id || "inst-001",
      code: req.body.code || "NEW-PROG",
      name: req.body.name || "New Programme",
      level: req.body.level || "UG",
      duration_semesters: req.body.duration_semesters || 8,
    };
    programmes.push(prog);
    res.status(201).json(prog);
  });

  app.get("/api/academic/courses", (req, res) => {
    res.json(courses);
  });

  app.post("/api/academic/courses", (req, res) => {
    const crs: Course = {
      id: `crs-${Date.now()}`,
      institution_id: institutions[0]?.id || "inst-001",
      code: req.body.code || "CRS",
      name: req.body.name || "New Course",
      credits: req.body.credits || 3,
      course_type: req.body.course_type || "THEORY",
      is_audit: !!req.body.is_audit,
    };
    courses.push(crs);
    res.status(201).json(crs);
  });

  app.get("/api/academic/regulations", (req, res) => {
    res.json(regulations);
  });

  app.post("/api/academic/regulations", (req, res) => {
    const reg: Regulation = {
      id: `reg-${Date.now()}`,
      institution_id: institutions[0]?.id || "inst-001",
      code: req.body.code || "REG",
      name: req.body.name || "New Regulation",
    };
    regulations.push(reg);
    res.status(201).json(reg);
  });

  // Vite middleware in dev; static file serving in production
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
