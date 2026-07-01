# AppStoreInfoProvider

## Description

A processor for AutoPkg that provides metadata from the iTunes/App Store Search API.

## Input variables

- **app_store_url:**
  - **required:** False
  - **description:** App Store URL (e.g., https://apps.apple.com/gb/app/name/id284882215)
- **app_store_id:**
  - **required:** False
  - **description:** App Store ID (e.g., 284882215)

## Output variables

- **track_name:**
  - **description:** Name of the app.
- **track_view_url:**
  - **description:** URL to the app in the App Store.
- **bundle_id:**
  - **description:** Bundle identifier.
- **version:**
  - **description:** Current version.
- **minimum_os_version:**
  - **description:** Minimum OS version required.
- **release_date:**
  - **description:** Release date.
- **description:**
  - **description:** App description.
- **seller_name:**
  - **description:** Developer/seller name.
- **track_id:**
  - **description:** App Store track ID.
- **artwork_path:**
  - **description:** Full path to downloaded artwork file.
