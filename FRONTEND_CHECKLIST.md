# Frontend Quick Start Checklist

## Prerequisites ✅
- [ ] Node.js 18+ installed
- [ ] FastAPI backend running on `http://localhost:8000`
- [ ] Ollama running with model available

## Setup Steps

### 1️⃣ Create Next.js Project
```bash
cd ..
npx create-next-app@latest sports-rag-frontend --typescript --tailwind --eslint --src-dir --app --import-alias "@/*" --no-git
cd sports-rag-frontend
```

### 2️⃣ Install Dependencies
```bash
npm install axios
```

### 3️⃣ Create Environment File
```bash
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### 4️⃣ Copy TypeScript Files

Copy code from `REACT_FRONTEND_GUIDE.md` to these files:

**File Creation Checklist:**
- [ ] `src/lib/api.ts` - API client (Section 1)
- [ ] `src/types/index.ts` - TypeScript types (Section 2)
- [ ] `src/components/SearchBar.tsx` - Search input (Section 3)
- [ ] `src/components/SportFilter.tsx` - Sport buttons (Section 4)
- [ ] `src/components/ResultsDisplay.tsx` - Results view (Section 5)
- [ ] `src/components/HealthCheck.tsx` - Health status (Section 6)
- [ ] `src/app/page.tsx` - Home page (Section 7)
- [ ] `src/app/layout.tsx` - Root layout (Section 8)
- [ ] `tailwind.config.ts` - Tailwind config (Section 9)
- [ ] `next.config.js` - Next config (Section 10)

### 5️⃣ Start Development Server
```bash
npm run dev
```

### 6️⃣ Test
```
Visit: http://localhost:3000
Expected: Search interface with Sports RAG header
```

---

## Verify Everything Works

### Backend Check
```powershell
curl http://localhost:8000/health
```
Should return: `{"status":"ok", ...}`

### Frontend Check
Open browser to: `http://localhost:3000`
Should show:
- Header "Sports RAG 🏆"
- Search bar
- Sport filter buttons
- Example questions

### Test Query
1. Click on an example question
2. Hit "Ask" button
3. Wait for answer
4. See sources appear below

---

## Common Commands

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Type check
npm run type-check

# Lint code
npm run lint

# Run production build
npm start
```

---

## File Locations Reference

```
C:\projects\
├── sports-rag/              (your backend)
│   ├── src/api/main.py      ← FastAPI backend
│   ├── .env                 ← Backend config
│   └── scripts/test_api.ps1 ← Test backend
│
└── sports-rag-frontend/     (your new frontend)
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx
    │   │   └── layout.tsx
    │   ├── components/
    │   │   ├── SearchBar.tsx
    │   │   ├── SportFilter.tsx
    │   │   ├── ResultsDisplay.tsx
    │   │   └── HealthCheck.tsx
    │   ├── lib/
    │   │   └── api.ts
    │   └── types/
    │       └── index.ts
    ├── .env.local
    ├── package.json
    └── next.config.js
```

---

## One-Line Commands

```bash
# Create project, install, configure, and run
npx create-next-app@latest sports-rag-frontend --typescript --tailwind --eslint --src-dir --app --import-alias "@/*" --no-git && cd sports-rag-frontend && npm install axios && echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Then copy the code files from REACT_FRONTEND_GUIDE.md

# Then run:
npm run dev
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot find module 'axios'" | Run `npm install axios` |
| "API not found (404)" | Check `NEXT_PUBLIC_API_URL` in `.env.local` |
| "Port 3000 already in use" | `npm run dev -- -p 3001` |
| "Module not found" errors | Restart dev server: `Ctrl+C` then `npm run dev` |
| TypeScript errors | Run `npm run type-check` |

---

## What's Next? 🚀

✅ Frontend is running  
✅ Can query the backend  
✅ Shows results with sources  

**Optional Enhancements:**
- Add chat history
- Dark mode
- User authentication
- Analytics
- Deploy to production

---

**You're all set!** Start with Step 1 above. 🎉
