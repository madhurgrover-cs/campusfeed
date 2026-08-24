"""
Shared CampusItem schema used by ALL connectors, regardless of source type.
This is the generalization fix: one schema definition, imported everywhere,
instead of each connector inlining its own event-shaped JSON.
"""

CAMPUS_ITEM_SCHEMA_PROMPT = """Return ONLY valid JSON, no markdown, no explanation, matching exactly this shape:

{
  "title": string,
  "item_type": "event" or "announcement" or "opportunity" or "notice" or "achievement" or "deadline" or "other",
  "organizer": string,
  "department": string or null,
  "category": string,
  "date_start": string or null,
  "date_end": string or null,
  "details": object,
  "notable_attendees": [string],
  "tags": [string],
  "confidence_notes": string,
  "tags": [string],
  "confidence_notes": string
}
}
}

Rules:
- item_type: pick the single best fit. Use "event" for hackathons/workshops/symposiums/cultural/sports.
  Use "announcement" for general notices/circulars. Use "opportunity" for internships/scholarships/placements.  Use "achievement" for faculty/student accomplishments.
- Use "deadline" ONLY for a cutoff with no associated happening. If an item has both a happening and a cutoff (e.g. a fest with a registration deadline), use "event" and put the cutoff in details.registration_deadline. If uncertain between event and deadline, choose "event".
  
  
- details: put type-specific facts here as key-value pairs (e.g. venue, registration_fee, prize_pool,
  team_size, eligibility, contact_info) - only include keys that are actually relevant and present.
  Do NOT force event-style fields onto non-event items.
- notable_attendees: names/titles of any VIPs, chief guests, dignitaries explicitly mentioned as attending
  or speaking. Empty array if none mentioned.
- date_start/date_end: normalize to YYYY-MM-DD where possible. Use null if not applicable or not stated.
- If a field is genuinely ambiguous or not present, use null and explain in confidence_notes.
- Do not invent information not present in the source content."""
