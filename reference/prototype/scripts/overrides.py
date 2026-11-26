# Analyst verification overrides (applied after automatic tagging). (regex on source_text, field updates)
OVR = [
 (r"jeff bezos' ai startup prometheus", dict(type='analysis-opinion', amount_usd=None, deal_status=None)),
 (r"elevenlabs is in early talks", dict(amount_usd=None, deal_status='in talks/reported', topic='Foundation models & AI labs', geography='Europe')),
 (r"plural raised a new €1bn fund|plural.{0,40}€1 ?bn fund", dict(topic='VC & startup ecosystem')),
 (r"sofinnova partners", dict(topic='VC & startup ecosystem')),
 (r"cohere completes the first close", dict(topic='Foundation models & AI labs', geography='Other')),
 (r"situational awareness is pitching", dict(type='news', amount_usd=None)),
 (r"bending spoons bought mailchimp", dict(amount_usd=None)),
 (r"isomorphic", dict(topic='Health & biotech')),
 (r"model ml", dict(topic='AI agents & enterprise AI')),
 (r"fractile", dict(topic='Chips & semiconductors', geography='Europe')),
 (r"payhawk", dict(topic='Fintech & crypto', geography='Europe')),
 (r"openai has (secured|closed on)", dict(amount_usd=11000000000, topic='Foundation models & AI labs')),
 (r"zipline", dict(geography='US')),
 (r"\bfal raised", dict(geography='US')),
 (r"jensen huang|nvidia'?s board", dict(topic='Chips & semiconductors')),
]
