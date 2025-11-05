# Jamf Object Reference

Certain Jamf API object types can be referenced in processors where the `object_type` key is provided. This document lists those objects available and the form that you must provide the object in.

| API Object | `object_type` Reference |
|-----------|--------------------------|
| Account User or Group | `account` |
| Account User | `account_user` |
| Account Group | `account_group` |
| Activation Code | `activation_code_settings` |
| Advanced Computer Search | `advanced_computer_search` |
| Advanced Mobile Device Search | `advanced_mobile_device_search` |
| API Client | `api_client` |
| API Role | `api_role` |
| Authorization Token (JPAPI) | `token` |
| Authorization Token (JPAPI - API Client) | `oauth` |
| Authorization Token (Platform API) | `platform_api_token` |
| App Installers Deployment | `app_installers_deployment` |
| App Installers Title | `app_installers_title` |
| App Installers T & C Settings | `app_installers_t_and_c_settings` |
| App Installers Accept T & C Command | `app_installers_accept_t_and_c_command` |
| Blueprint | `blueprint` |
| Blueprint - Deploy | `blueprint_deploy` |
| Blueprint - Undeploy | `blueprint_undeploy` |
| Category | `category` |
| Check-In Settings | `check_in_settings` |
| Cloud LDAP | `cloud_ldap` |
| Compliance Benchmarks - Baseline | `baseline` |
| Compliance Benchmarks - Benchmark | `benchmark` |
| Compliance Benchmarks - Rule | `rule` |
| Computer | `computer` |
| Computer Extension Attribute | `computer_extension_attribute` |
| Computer Group (Smart or Static) | `computer_group` |
| Computer Inventory Collection Settings | `computer_inventory_collection_settings` |
| Computer PreStage Enrollment | `computer_prestage` |
| Computer Configuration Profile | `os_x_configuration_profile` |
| Distribution Point | `distribution_point` |
| Dock Item | `dock_item` |
| Enrollment Settings | `enrollment_settings` |
| Enrollment Customization | `enrollment_customization` |
| Failover | `failover` |
| Failover Generate Command | `failover_generate_command` |
| Group (Computer or Mobile Device) | `group` |
| Icon | `icon` |
| Jamf Pro Version | `jamf_pro_version_settings` |
| Jamf Protect Plans Sync | `jamf_protect_plans_sync_command` |
| Jamf Protect - Register | `jamf_protect_register_settings` |
| Jamf Protect Settings | `jamf_protect_settings` |
| JCDS | `jcds` |
| LAPS | `laps_settings` |
| LDAP Server | `ldap_server` |
| Mac App Store or In-House Application | `mac_application` |
| Managed Software Updates - Available Updates | `managed_software_updates_available_updates` |
| Managed Software Updates - Feature Toggle | `managed_software_updates_feature_toggle_settings` |
| Managed Software Updates - Plans | `managed_software_updates_plans` |
| Managed Software Updates - Plans - Events | `managed_software_updates_plans_events` |
| Managed Software Updates - Plans - Group Settings | `managed_software_updates_plans_group_settings` |
| Managed Software Updates - Update Statuses | `managed_software_updates_update_statuses` |
| Mobile Device | `mobile_device` |
| Mobile Device App Store or In-House Application | `mobile_device_application` |
| Mobile Device Configuration Profile | `configuration_profile` |
| Mobile Device Extension Attribute (Classic API) | `mobile_device_extension_attribute` |
| Mobile Device Extension Attribute (JPAPI) | `mobile_device_extension_attribute_v1` |
| Mobile Device Group (Smart or Static) | `mobile_device_group` |
| Mobile Device PreStage Enrollment | `mobile_device_prestage` |
| Network Segment | `network_segment` |
| Package Object (Classic API) | `package` |
| Package (JPAPI) | `package_v1` |
| Package Upload (unofficial, deprecated) | `dbfileupload` |
| Patch Policy | `patch_policy` |
| Patch Software Title | `patch_software_title` |
| Policy | `policy` |
| Policy Icon | `policy_icon` |
| Policy Log Flush | `logflush` |
| Policy Properties | `policy_properties_settings` |
| Restricted Software | `restricted_software` |
| Script | `script` |
| Self Service | `self_service_settings` |
| Self Service+ | `self_service_plus_settings` |
| Smart Computer Group Membership | `smart_computer_group_membership` |
| SMTP Server | `smtp_server_settings` |
| SSO Certificate | `sso_cert_command` |
| SSO | `sso_settings` |
| Volume Purchasing Location | `volume_purchasing_location` |
