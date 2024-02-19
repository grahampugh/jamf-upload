#!/bin/bash

# these repos needed
autopkg repo-add nstrauss-recipes recipes hjuutilainen-recipes ahousseini-recipes homebysix-recipes novaksam-recipes nzmacgeek-recipes hansen-m-recipes keeleysam-recipes rtrouton-recipes joshua-d-miller-recipes nmcspadden-recipes dataJAR-recipes tbridge-recipes amsysuk-recipes killahquam-recipes crystalllized-recipes scriptingosx-recipes

for recipe in "$HOME/Library/AutoPkg/RecipeRepos/com.github.autopkg.grahampugh-recipes/Jamf_Recipes/"*; do
    echo
    echo "RUNNING ${recipe/\.recipe$/}"
    autopkg run -v "${recipe/\.recipe$/}"
    echo
done
