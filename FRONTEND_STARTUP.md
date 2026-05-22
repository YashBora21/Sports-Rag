# 🚀 FRONTEND STARTUP GUIDE

## ✅ You've Created All Files!

Now let's verify and start the frontend.

---

## Step 1: Verify File Structure

In your `sports-rag-frontend` folder, you should have:

```
sports-rag-frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── SearchBar.tsx
│   │   ├── SportFilter.tsx
│   │   ├── ResultsDisplay.tsx
│   │   └── HealthCheck.tsx
│   ├── lib/
│   │   └── api.ts
│   ├── types/
│   │   └── index.ts
│   └── app/globals.css
├── public/
├── .env.local                 ← Must have this!
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── node_modules/              ← Should have this after npm install
```

**Check .env.local exists:**
```bash
cat .env.local
# Should output: NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Step 2: Verify Dependencies

Make sure all npm packages are installed:

```bash
# Check if node_modules exists
dir node_modules

# If empty or missing, install:
npm install

# Verify axios is installed
npm list axios
# Should show: axios@1.6.7 (or similar)
```

---

## Step 3: Type Check (Optional but Recommended)

Make sure TypeScript has no errors:

```bash
npm run type-check
```

If errors appear, they'll show the file and line number. Fix them before proceeding.

---

## Step 4: Start Backend (if not running)

**In a SEPARATE PowerShell window**, make sure your FastAPI backend is running:

```powershell
cd ..\sports-rag
(venv) PS C:\projects\sports-rag> uvicorn src.api.main:app --reload --port 8000
```

You should see:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Leave this running!** (Don't close this window)

---

## Step 5: Start Frontend Dev Server

**In a NEW PowerShell window** (keep backend running in the other):

```powershell
cd C:\projects\sports-rag-frontend
npm run dev
```

You should see:
```
> sports-rag-frontend@1.0.0 dev
> next dev

  ▲ Next.js 14.1.0
  - Local:        http://localhost:3000
  - Environments: .env.local

✓ Ready in 1234ms
```

---

## Step 6: Test Frontend

Open your browser to: **http://localhost:3000**

You should see:
```
┌─────────────────────────────────────┐
│     Sports RAG 🏆                   │
│ Ask any sports question.            │
│ Powered by Ollama Gemma4 + FAISS    │
├─────────────────────────────────────┤
│ ✓ API Status: OK                    │
├─────────────────────────────────────┤
│ [Search box]                        │
│ [Ask] button                        │
├─────────────────────────────────────┤
│ Filter by Sport:                    │
│ [All] [Football] [Basketball] ...   │
├─────────────────────────────────────┤
│ Try these questions:                │
│ • Who won the 2022 World Cup?       │
│ • What is Cristiano Ronaldo...      │
│ • Who won the 2023 NBA...           │
└─────────────────────────────────────┘
```

---

## Step 7: Test a Query

1. Click on an example question (or type your own)
2. Click the **[Ask]** button (or press Enter)
3. You should see: "Thinking..." with a spinner
4. After 2-5 seconds: Answer appears!
5. Sources appear below with relevance scores

Expected output:
```
ANSWER
Argentina won the 2022 FIFA World Cup, defeating France in the final...

⏱️ Retrieval: 234ms | LLM: 1234ms | Total: 1468ms

📚 RETRIEVED SOURCES (5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FOOTBALL    Score: 98%
"Argentina's national team won the 2022 World Cup in Qatar..."
📌 FIFA - World Cup Summary.csv

FOOTBALL    Score: 95%
"In the final match, Argentina defeated France on penalties..."
📌 FIFA - 2022.csv
```

---

## 🎯 Full Terminal Setup (Side by Side)

### Terminal 1 (Backend)
```powershell
cd C:\projects\sports-rag
venv\Scripts\activate
uvicorn src.api.main:app --reload --port 8000
```

Should show:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Terminal 2 (Frontend)
```powershell
cd C:\projects\sports-rag-frontend
npm run dev
```

Should show:
```
✓ Ready in 1234ms
- Local: http://localhost:3000
```

### Browser
Open: **http://localhost:3000**

**Both should be running simultaneously!**

---

## ⚠️ Troubleshooting

### Issue 1: "Cannot connect to API"
**Problem:** Frontend can't reach backend

**Solutions:**
```bash
# 1. Check backend is running
curl http://localhost:8000/health

# 2. Check .env.local has correct URL
cat .env.local

# 3. Check NEXT_PUBLIC_API_URL is set
$env:NEXT_PUBLIC_API_URL
```

### Issue 2: "Port 3000 already in use"
**Problem:** Another process using port 3000

**Solution:**
```bash
# Run on different port
npm run dev -- -p 3001
# Visit http://localhost:3001
```

### Issue 3: Blank page or error
**Problem:** Frontend not loading

**Solutions:**
```bash
# 1. Check browser console for errors
# F12 → Console tab → look for red errors

# 2. Restart dev server
# Ctrl+C in terminal
# npm run dev

# 3. Clear browser cache
# Ctrl+Shift+Delete → Clear all
```

### Issue 4: API returns 404 or 503
**Problem:** Backend not ready or FAISS index not loaded

**Solution:**
```bash
# In sports-rag folder, rebuild index:
python scripts/run_pipeline.py --data-dir data/raw
```

### Issue 5: "Module not found" errors
**Problem:** Missing npm packages

**Solution:**
```bash
npm install
npm run type-check
```

### Issue 6: Timeout during query
**Problem:** Ollama Cloud model is slow or overloaded

**Solution:**
```env
# In .env (backend), reduce tokens:
LLM_MAX_TOKENS=512

# Or use faster model:
OLLAMA_MODEL="mistral"
```

---

## 📊 Checking Everything Works

### Checklist:

- [ ] Frontend folder created with all files
- [ ] `npm install` completed (node_modules exists)
- [ ] `.env.local` exists with correct API_URL
- [ ] Backend running on http://localhost:8000
- [ ] Frontend running on http://localhost:3000
- [ ] Browser shows "Sports RAG 🏆" header
- [ ] Health status shows "✓ OK"
- [ ] Example questions are clickable
- [ ] Clicking example question → "Thinking..." spinner
- [ ] Answer appears after 2-5 seconds
- [ ] Sources appear below answer

**If all checked ✓, you're ready to use!**

---

## 🎉 What To Do Next

### Test Different Queries
Try different questions:
```
Who won the 2022 World Cup?
What is Lionel Messi's club?
Who scored the most NBA points?
Which cricket team won the IPL 2024?
```

### Filter by Sport
Try filtering by sport:
```
Question: Who won the final?
Filter: Football → Get football results only
Filter: Cricket → Get cricket results only
```

### Check API Docs
Visit: http://localhost:8000/docs
- See all available endpoints
- Try endpoints directly

### Monitor Performance
- Watch latency_ms values
- Usually: 200-500ms retrieval + 1000-2000ms LLM
- Total should be 1-3 seconds

---

## 📱 Optional: Test on Mobile

### Local Network Test
```bash
# Find your PC IP
ipconfig | findstr IPv4

# Example: 192.168.1.100

# Open on phone browser:
http://192.168.1.100:3000
```

---

## 🔧 Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Run production build locally
npm start

# Type check (find TypeScript errors)
npm run type-check

# Lint code (find style issues)
npm run lint

# Stop dev server
Ctrl+C
```

---

## 📝 Debugging Tips

### Enable Browser DevTools
```
Press F12
→ Console tab: see JavaScript errors
→ Network tab: see API calls
→ Elements tab: inspect HTML/CSS
```

### Check Network Requests
1. F12 → Network tab
2. Make a query
3. Look for "query" POST request
4. Click it to see:
   - Request body (your question)
   - Response (answer + sources)
   - Response time

### Check Logs
```bash
# Terminal window 1 (backend)
# Shows every API request:
POST /query → 200 OK (1234ms)

# Terminal window 2 (frontend)
# Shows build warnings/errors
```

---

## ✨ Success Indicators

Your frontend is working correctly when:

✅ Page loads at http://localhost:3000  
✅ Header says "Sports RAG 🏆"  
✅ Health status shows "OK"  
✅ Example questions appear  
✅ Search bar is responsive  
✅ Queries return answers in 1-3 seconds  
✅ Sources appear with scores  
✅ Sport filter buttons work  
✅ No errors in browser console  
✅ No errors in terminal  

---

## 🎊 Congratulations!

You now have a **complete Sports RAG system**:

✅ Python backend with Ollama Gemma4  
✅ FAISS vector search  
✅ React + Next.js + TypeScript frontend  
✅ Beautiful Tailwind CSS UI  
✅ Real-time queries with sources  

**Ready to deploy or customize further!** 🚀

---

## Next Steps

### 1. Deploy Backend
- Heroku, PythonAnywhere, or cloud VPS
- Update frontend `.env.local` with production URL

### 2. Deploy Frontend
- Vercel (easiest for Next.js)
- GitHub Pages
- Docker container

### 3. Customize
- Add more sports to filter
- Change colors/branding
- Add chat history
- Add authentication

### 4. Optimize
- Cache queries
- Compress responses
- Add pagination
- Monitor performance

---

**Enjoy your Sports RAG system!** 🏆⚡
