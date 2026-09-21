# Affiliate Blog — One-Time Setup (Brian's steps only)

This one can't be fully automated because it needs your identity/account
approval — but unlike Etsy, **neither step here requires a government-ID
check.** GitHub signup is just an email/password; Amazon Associates approval
is based on having a real site with real content (which this already
produces), not ID verification.

## 1. The site itself — already done
- Live at: **https://bclarknc-tech.github.io/everyday-upgrade-picks/**
- Hosted free on GitHub Pages, auto-rebuilds a minute or two after every
  scheduled run.
- Repo: https://github.com/bclarknc-tech/everyday-upgrade-picks

## 2. Apply for Amazon Associates (do this once)
1. Go to https://affiliate-program.amazon.com/ and sign up (use your normal
   Amazon account).
2. When it asks for your website, use the link above — Amazon wants to see
   real content before approving, which this site already has.
3. Amazon will ask a few questions about how you drive traffic (be honest —
   e.g. "content site with buying guides") and give you a **tracking ID**
   that looks like `yourname-20`.
4. Amazon requires you to make **3 qualifying sales within 180 days** or
   your account gets closed (you can just reapply later — no penalty beyond
   losing that particular tag). Sharing the site link anywhere real people
   will see it (social media, forums, friends) is what makes that happen —
   the site itself won't get organic traffic on its own.

## 3. Plug in your tracking ID
One time, in PowerShell:
```
setx AMAZON_ASSOCIATE_TAG "yourname-20"
```
Until you do this, the site still generates and publishes fine — the links
just carry a placeholder tag (`PLACEHOLDER-20`) that won't pay out anything.

## 4. That's it
The "Jarvis - Affiliate Blog Generator" scheduled task runs every Wednesday
6am, writes 3 new buying-guide articles, and pushes them live automatically.
Check in on it any time at the site link above, or the repo's commit history.
