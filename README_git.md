# Synchronising 

To update your clean local main from AIS:

````
git switch main
git fetch upstream
git merge --ff-only upstream/main
git push origin main
````

Then update your feature branch:

````
git switch investigation/phi-finder-pipeline
git rebase main
````
## Recommended order now
1. Create the personal fork.
1. Rename the current AIS remote to upstream.
1. Add your fork as origin.
1. Push main.
1. Create and push investigation/phi-finder-pipeline.
1. Review git status --short.
1. Exclude generated local artefacts.
1. Only then decide what actual source or documentation changes to commit.