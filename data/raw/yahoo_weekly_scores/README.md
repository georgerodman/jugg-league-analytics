# Yahoo weekly scores

Authenticated Yahoo Fantasy Football archive capture for league key `cowboys10`.
Each season file contains the five final regular-season matchups for every week,
the season-specific team IDs and names, and the source league URL. Files are
written only after every week validates as a complete 10-team slate.

The downstream hybrid calculation awards one point for a head-to-head win and
one point for scoring strictly above that week's 10-team median. A head-to-head
tie awards 0.5; a score exactly equal to the median earns no median point.
