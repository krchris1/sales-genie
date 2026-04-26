# Sales Genie

Your magical selling assistant. Take photos, AI cleans them up and writes the listing, share it to eBay / Facebook Marketplace / OfferUp / Craigslist / Nextdoor — and let a smart AI co-pilot help you handle buyer messages.

The whole app is a single file (`index.html`) that runs in your phone's browser. No backend, no app store, no install. Your photos and drafts stay on your device.

## What's in the box

**Guided sales flow**
- Welcome → "What are you selling?" category picker → item type → photos → details → AI generates → review → post
- Or skip the pickers entirely: tap "✨ AI pick from a photo" and the genie figures out what it is

**AI photo cleanup**
- Background removal runs on your phone (open-source model, ~80MB once, then offline)
- Optional white-background composite for clean catalog-style shots

**AI listing writer (Claude vision)**
- Title, honest description, suggested price range, category, tags
- Flags things you should double-check ("I couldn't see the back from these photos")
- "✨ Make it better" / "Shorter" / "More honest" one-tap rewrites

**Listing health & gamification**
- Each listing scored 0-100 (photos ✓, description ✓, price ✓, tags ✓, flags ✓) with a progress ring
- Home-screen stats: total earned, items sold, posts this week 🔥
- Confetti when you generate a listing or mark one sold

**Smart sales co-pilot for buyer chats**
- Detects intent: real interest, lowball, scam, logistics question, going silent
- Drafts replies tuned to the situation with concrete sales tactics
- One-tap follow-ups ("Counter at $X", "Confirm pickup", "Decline politely")
- Warns about Google Voice scams, "my agent will pick up", wire transfer requests
- Remembers the whole conversation per buyer

**Sales tracking (works for all 5 platforms today)**
- Mark which platforms you posted to
- Log offers as they come in
- Mark items sold (price + platform), track profit across platforms
- "My sales" dashboard with totals and recent activity

**Marketplace handoff**
- Primary: native phone share sheet — tap "Share to apps" and pick eBay / Facebook / OfferUp / Messages / wherever
- Fallback: per-platform buttons that copy the listing and open the create-listing page

## What you need

- **A Claude API key.** Free to make at https://console.anthropic.com — first $5 in credits is free. Each generated listing costs roughly 1-2¢; chat replies are fractions of a cent.
- **A way to put `index.html` somewhere your phone can reach.** Easiest options below.

## Get it on your phone in ~3 minutes

### Option A — Vercel (easiest, free, gets you an HTTPS link)

1. Make a free account at https://vercel.com
2. Open https://vercel.com/new and click "Continue with no Git source" (or drag the folder onto the page)
3. Drag the whole `crosslist-ai` folder onto the page
4. Click Deploy
5. You'll get a URL like `sales-genie-abcd.vercel.app`
6. On your phone, open that URL in Safari (iOS) or Chrome (Android)
7. Tap the share icon → "Add to Home Screen" so it lives next to your other apps

### Option B — Netlify Drop

Go to https://app.netlify.com/drop, drag the folder onto the page, get an HTTPS URL.

### Option C — GitHub Pages

Make a public repo, drag `index.html` in via the GitHub web UI, enable Pages in Settings.

### Option D — Local-only

```bash
cd crosslist-ai
npm start    # uses `npx serve`
```

To open from your phone, your laptop and phone need to be on the same Wi-Fi, and you'd open something like `http://192.168.1.42:3000`. Note: camera and AI-image-edit features need HTTPS, so for production use, deploy to Option A.

## First-time setup (on your phone)

1. Open the URL.
2. Paste your Claude API key in Settings (stored only on your device).
3. Welcome screen explains how it works.
4. Tap "+ New listing" or use the magic photo categorizer to start.

## How posting actually works

The "Share to apps" button uses your phone's native share sheet — same one you get when you share anything else. It hands the listing text and all photos to whichever app you tap. eBay, Facebook, OfferUp, and Messages all accept this. Some apps will pre-fill a listing form; others paste the content into a new post.

This is as close to one-tap posting as the platforms allow:

- **eBay** is the only platform with a public posting API, and it requires OAuth + a server callback. We can build that as a Phase 2 add-on (see roadmap below). The eBay app itself receives shared content and pre-fills the listing form.
- **Facebook Marketplace, OfferUp, Craigslist, Nextdoor** have no public posting APIs. Anything that automates posting on those platforms violates terms of service and gets accounts banned. The native share-sheet approach is the cleanest legitimate path.

## How the chat assistant works

Open any draft → "💬 Reply to a buyer". Paste the buyer's message and the Genie drafts a reply tuned to the situation:

- **Real interest** → moves toward closing (asks for pickup time, etc.)
- **Lowball offer** → polite counter, doesn't get offended
- **Logistics question** → answers, suggests a public meet-up for higher-value items
- **Scam pattern** → warns you and drafts a polite decline
- **Buyer went silent** → suggests a soft re-engage

After each suggested reply, you'll see one-tap follow-ups (e.g. "Confirm pickup", "Counter at $X") to nudge the conversation. Replies are suggestions — the actual sending happens in your marketplace app. Tap "Copy" or "Share to app" to bring the reply into wherever the buyer messaged you.

## Privacy & safety

- Your Claude API key is stored only in your phone's browser (`localStorage`). Nobody else sees it.
- Drafts and photos live in your phone's browser storage (`IndexedDB`).
- Photos are sent to Anthropic when you generate a listing or chat (Claude has to see them). Nothing is sent to any other third party.
- Background-removal model runs entirely on your device — those photos never leave your phone.
- Marketplace posting happens in the marketplace's own app/website. Sales Genie has no access to your marketplace accounts.

## Roadmap (what's next)

These are the next builds, deliberately scoped because each requires real work beyond what fits in a single session.

### Phase 2 — Real eBay integration
Adds a small backend (Node.js or Cloudflare Workers) that handles eBay's OAuth flow. Once it ships, you'll be able to:
- Log into your eBay account once and never see the OAuth screen again
- Post listings directly from Sales Genie (no copy-paste)
- See your live eBay listings inside Sales Genie
- Pull buyer messages into the chat assistant automatically

eBay-only — the other four platforms don't expose this kind of API to anyone.

### Phase 3 — Browser extension for desktop auto-fill
A Chrome/Firefox extension that fills the create-listing form on Facebook Marketplace, OfferUp, Craigslist, and Nextdoor when you're posting from your own browser. This is how the paid cross-listing services (Vendoo, List Perfectly) work for these platforms — there's no API to integrate, but a logged-in browser extension can fill the form for you. Desktop-only.

### Phase 4 — Premium image staging (optional)
Hook up Photoroom or a similar API for AI-staged backgrounds (place your couch in a "stylish living room", put the watch on a clean white surface). Would replace the current local background removal with cloud calls and add a small per-image cost (~$0.01-0.10).

## Limits & gotchas

- **Storage:** Browsers cap site storage somewhere between 50MB and several GB. Hundreds of drafts with lots of photos may hit limits.
- **iOS Safari Private mode** disables IndexedDB. Use a normal tab.
- **Background removal first run** downloads ~80MB. Be on Wi-Fi the first time.
- **Single-user only.** Multiple people on the same phone share one set of drafts. (Multi-user needs a backend.)
- **Cost:** Generating a listing with Claude costs roughly $0.01-0.03; chat replies are typically under $0.01. The first $5 is free with a new Anthropic account.

## Folder layout

```
crosslist-ai/         (project folder; can be renamed if you want)
├── index.html        # the entire app
├── README.md         # this file
├── package.json      # `npm start` runs a local static server
└── backend/          # leftover from an earlier draft, can be deleted
```
