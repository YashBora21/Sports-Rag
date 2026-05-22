# Sports RAG Frontend - React + Next.js + TypeScript Setup

## Quick Start

```bash
# 1. Create Next.js project with TypeScript
cd ..
npx create-next-app@latest sports-rag-frontend --typescript --tailwind --eslint

# 2. Choose options:
# - Use TypeScript: Yes
# - Use ESLint: Yes
# - Use Tailwind: Yes
# - Use src/ directory: Yes
# - Use App Router: Yes
# - Import alias: @/*

# 3. Navigate and install dependencies
cd sports-rag-frontend
npm install axios

# 4. Set API endpoint
# Create .env.local:
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 5. Start dev server
npm run dev
# Visit http://localhost:3000
```

## Project Structure

```
sports-rag-frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Home page
│   │   └── globals.css        # Tailwind styles
│   ├── components/
│   │   ├── SearchBar.tsx      # Query input
│   │   ├── ResultsDisplay.tsx # Answer + sources
│   │   ├── HealthCheck.tsx    # API status
│   │   └── SportFilter.tsx    # Sport selector
│   ├── lib/
│   │   └── api.ts             # API client
│   └── types/
│       └── index.ts           # TypeScript types
├── .env.local                  # API_URL
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

## Key Features

✅ **Clean Modern UI** - Tailwind CSS + Heroicons
✅ **Real-time Search** - Type and get instant results
✅ **Sport Filter** - Football, NBA, Cricket, Tennis
✅ **Source Display** - Show retrieved chunks with scores
✅ **Health Status** - Display API health
✅ **Loading States** - Smooth UX during queries
✅ **Error Handling** - User-friendly error messages
✅ **Responsive Design** - Mobile + tablet + desktop

## Installation Steps (Manual)

### Step 1: Create Next.js App
```bash
npx create-next-app@latest sports-rag-frontend \
  --typescript \
  --tailwind \
  --eslint \
  --src-dir \
  --app \
  --import-alias "@/*"
```

### Step 2: Install Dependencies
```bash
cd sports-rag-frontend
npm install axios
```

### Step 3: Create .env.local
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 4: Copy Components & Files
- Copy provided TypeScript files to src/components, src/app, src/lib, src/types

### Step 5: Run Development Server
```bash
npm run dev
```

Visit: http://localhost:3000

## Files Provided

1. **next.config.js** - Next.js configuration with CORS proxy
2. **tsconfig.json** - TypeScript config
3. **tailwind.config.ts** - Tailwind customization
4. **app/layout.tsx** - Root layout with metadata
5. **app/page.tsx** - Home page with search interface
6. **components/SearchBar.tsx** - Query input component
7. **components/ResultsDisplay.tsx** - Answer & sources display
8. **components/HealthCheck.tsx** - API health status
9. **components/SportFilter.tsx** - Sport selection
10. **lib/api.ts** - Axios client with error handling
11. **types/index.ts** - TypeScript interfaces

## Deployment

### Development
```bash
npm run dev
```

### Production Build
```bash
npm run build
npm start
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## API Integration

The frontend calls your FastAPI backend at `NEXT_PUBLIC_API_URL`:

- **GET /health** - Check API status
- **POST /query** - Submit RAG query
  - Request: `{question, sport_filter?, top_k?}`
  - Response: `{answer, sources, latency_ms}`

## Styling

- **Tailwind CSS** for styling
- **Heroicons** for icons
- **Dark mode ready** - add dark: classes as needed
- **Responsive** - mobile-first design

## Troubleshooting

### CORS Errors
Make sure FastAPI has CORS enabled (already in your config)

### API Not Responding
Check: `NEXT_PUBLIC_API_URL` matches your backend URL

### Build Errors
Run: `npm run type-check` to verify TypeScript

## Next Steps

1. Generate Next.js project: `npx create-next-app...`
2. Copy TypeScript files
3. Start dev server: `npm run dev`
4. Visit http://localhost:3000
5. Make API calls to http://localhost:8000

Enjoy! 🚀
