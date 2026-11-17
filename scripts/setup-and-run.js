#!/usr/bin/env node
/**
 * AI Resume Screening System — Dev Orchestrator
 * Checks Python environment, creates venv, manages dependencies,
 * initializes database if needed, and starts backend + frontend concurrently.
 */
const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');
const crypto = require('crypto');

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_DIR = path.join(ROOT_DIR, 'backend');
const FRONTEND_DIR = path.join(ROOT_DIR, 'frontend');
const VENV_DIR = path.join(ROOT_DIR, '.venv');
const REQUIREMENTS_FILE = path.join(BACKEND_DIR, 'requirements.txt');
const HASH_FILE = path.join(VENV_DIR, '.requirements_hash');

const isWin = process.platform === 'win32';
const venvPython = isWin
  ? path.join(VENV_DIR, 'Scripts', 'python.exe')
  : path.join(VENV_DIR, 'bin', 'python');

function killProcess(proc) {
  if (!proc || !proc.pid) return;
  try {
    if (isWin) {
      execSync(`taskkill /pid ${proc.pid} /T /F`, { stdio: 'ignore' });
    } else {
      process.kill(-proc.pid, 'SIGTERM');
    }
  } catch (e) {
    try {
      proc.kill('SIGTERM');
    } catch (_) {}
  }
}

function findSystemPython() {
  const candidates = isWin
    ? ['python', 'py -3', 'py', 'python3']
    : ['python3', 'python'];

  for (const cmd of candidates) {
    try {
      const res = execSync(`${cmd} --version`, { stdio: 'pipe' }).toString();
      if (res.toLowerCase().includes('python')) {
        return cmd;
      }
    } catch (e) {
      // try next
    }
  }
  return null;
}

function getRequirementsHash() {
  if (!fs.existsSync(REQUIREMENTS_FILE)) return '';
  const content = fs.readFileSync(REQUIREMENTS_FILE, 'utf-8');
  return crypto.createHash('sha256').update(content).digest('hex');
}

function setupPythonEnvironment() {
  console.log('\n[1/4] Checking Python environment...');

  if (!fs.existsSync(venvPython)) {
    const sysPython = findSystemPython();
    if (!sysPython) {
      console.error('\n❌ ERROR: Python 3.10+ was not found on your system PATH.');
      console.error('Please install Python from https://www.python.org/downloads/ and ensure "Add Python to PATH" is checked.\n');
      process.exit(1);
    }

    console.log(`Creating Python virtual environment at ${VENV_DIR}...`);
    try {
      execSync(`${sysPython} -m venv "${VENV_DIR}" --system-site-packages`, {
        cwd: ROOT_DIR,
        stdio: 'inherit',
      });
    } catch (_) {
      execSync(`${sysPython} -m venv "${VENV_DIR}"`, {
        cwd: ROOT_DIR,
        stdio: 'inherit',
      });
    }
    console.log('✅ Virtual environment created.');
  } else {
    console.log(`✅ Using virtual environment: ${venvPython}`);
  }

  // Verify core modules
  let modulesOk = false;
  try {
    execSync(`"${venvPython}" -c "import fastapi, uvicorn, sqlalchemy"`, {
      stdio: 'pipe',
    });
    modulesOk = true;
  } catch (_) {
    modulesOk = false;
  }

  const currentHash = getRequirementsHash();
  let installedHash = '';
  if (fs.existsSync(HASH_FILE)) {
    try {
      installedHash = fs.readFileSync(HASH_FILE, 'utf-8').trim();
    } catch (_) {}
  }

  if (!modulesOk || (currentHash && currentHash !== installedHash)) {
    console.log('[2/4] Installing / updating backend dependencies from requirements.txt...');
    try {
      execSync(`"${venvPython}" -m pip install -r "${REQUIREMENTS_FILE}"`, {
        cwd: BACKEND_DIR,
        stdio: 'inherit',
      });
      if (currentHash) {
        fs.writeFileSync(HASH_FILE, currentHash, 'utf-8');
      }
      console.log('✅ Backend dependencies installed.');
    } catch (err) {
      if (modulesOk) {
        console.warn('⚠️  Pip install had warnings/errors, but required core modules are present. Continuing...');
      } else {
        console.error('❌ Failed to install required backend dependencies:', err.message);
        process.exit(1);
      }
    }
  } else {
    console.log('[2/4] Backend dependencies are verified (cached).');
  }

  // Database initialization check
  const dbFile = path.join(BACKEND_DIR, 'ai_ats.db');
  if (!fs.existsSync(dbFile)) {
    console.log('Initializing local database schema & default seed data...');
    try {
      execSync(`"${venvPython}" "${path.join(BACKEND_DIR, 'init_db.py')}"`, {
        cwd: BACKEND_DIR,
        stdio: 'inherit',
      });
    } catch (e) {
      console.warn('Database init note:', e.message);
    }
  }
}

function startServers() {
  console.log('[3/4] Launching Backend API (FastAPI / Uvicorn on http://localhost:8000)...');
  const backendProc = spawn(
    venvPython,
    ['-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'],
    {
      cwd: BACKEND_DIR,
      stdio: 'inherit',
      shell: false,
    }
  );

  console.log('[4/4] Launching Frontend (Vite / React on http://localhost:8081)...');
  const npmCmd = isWin ? 'npm.cmd' : 'npm';
  const frontendProc = spawn(npmCmd, ['run', 'dev'], {
    cwd: FRONTEND_DIR,
    stdio: 'inherit',
    shell: isWin,
  });

  const banner = () => {
    console.log('\n' + '='.repeat(64));
    console.log('  ✨ AI Resume Screening System is running!');
    console.log('');
    console.log('  🌐 Frontend Application:  http://localhost:8081');
    console.log('  🔌 Backend API:           http://localhost:8000');
    console.log('  📚 API Documentation:     http://localhost:8000/docs');
    console.log('='.repeat(64) + '\n');
  };

  setTimeout(banner, 2000);

  let isCleaningUp = false;
  const cleanup = () => {
    if (isCleaningUp) return;
    isCleaningUp = true;
    console.log('\n🛑 Stopping servers...');
    killProcess(backendProc);
    killProcess(frontendProc);
    process.exit(0);
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);
  process.on('exit', cleanup);

  backendProc.on('exit', (code) => {
    if (!isCleaningUp && code !== 0 && code !== null) {
      console.error(`Backend process exited with code ${code}`);
    }
  });

  frontendProc.on('exit', (code) => {
    if (!isCleaningUp && code !== 0 && code !== null) {
      console.error(`Frontend process exited with code ${code}`);
    }
  });
}

setupPythonEnvironment();
startServers();

