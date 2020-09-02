#!/usr/local/autopkg/python

"""
A processor for uploading a category to Jamf Pro using AutoPkg
    by G Pugh

"""

import json
import requests
from base64 import b64encode
from time import sleep
from autopkglib import Processor, ProcessorError  # pylint: disable=import-error


class JamfCategoryUploader(Processor):
    """A processor for AutoPkg that will upload a category to a Jamf Cloud or on-prem server."""

    input_variables = {
        "JSS_URL": {
            "required": True,
            "description": "URL to a Jamf Pro server that the API user has write access "
            "to, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_USERNAME": {
            "required": True,
            "description": "Username of account with appropriate access to "
            "jss, optionally set as a key in the com.github.autopkg "
            "preference file.",
        },
        "API_PASSWORD": {
            "required": True,
            "description": "Password of api user, optionally set as a key in "
            "the com.github.autopkg preference file.",
        },
        "category": {"required": False, "description": "Category", "default": "",},
        "priority": {
            "required": False,
            "description": "Category priotity",
            "default": "10",
        },
    }

    output_variables = {
        "category": {"description": "The created/updated category.",},
        "jamfcategoryuploader_summary_result": {
            "description": "Description of interesting results.",
        },
    }

    def get_uapi_token(self, jamf_url, enc_creds):
        """get a token for the Jamf Pro API"""
        headers = {
            "authorization": "Basic {}".format(enc_creds),
            "content-type": "application/json",
            "accept": "application/json",
        }
        url = "{}/uapi/auth/tokens".format(jamf_url)
        http = requests.Session()
        r = http.post(url, headers=headers)
        self.output(
            r.content, verbose_level=2,
        )
        if r.status_code == 200:
            obj = json.loads(r.text)
            try:
                token = str(obj["token"])
                self.output("Session token received")
                return token
            except KeyError:
                self.output("ERROR: No token received")
                return
        else:
            self.output("ERROR: No token received")
            return

    def get_uapi_obj_id_from_name(self, jamf_url, object_type, object_name, token):
        """The UAPI doesn't have a name object, so we have to get the list of scripts 
        and parse the name to get the id """
        headers = {
            "authorization": "Bearer {}".format(token),
            "accept": "application/json",
        }
        url = "{}/uapi/v1/{}".format(jamf_url, object_type)
        http = requests.Session()

        r = http.get(url, headers=headers)
        if r.status_code == 200:
            object_list = json.loads(r.text)
            obj_id = 0
            for obj in object_list["results"]:
                self.output(
                    obj, verbose_level=2,
                )
                if obj["name"] == object_name:
                    obj_id = obj["id"]
            return obj_id

    def upload_category(self, jamf_url, category_name, priority, token, obj_id=0):
        """Update category metadata."""

        # build the object
        category_data = {"priority": priority, "name": category_name}
        headers = {
            "authorization": "Bearer {}".format(token),
            "content-type": "application/json",
            "accept": "application/json",
        }
        if obj_id:
            url = "{}/uapi/v1/categories/{}".format(jamf_url, obj_id)
            category_data["name"] = category_name
        else:
            url = "{}/uapi/v1/categories".format(jamf_url)

        http = requests.Session()

        print("Uploading category..")

        count = 0
        category_json = json.dumps(category_data)

        # we cannot PUT a category of the same name due to a bug in Jamf Pro (PI-008157).
        # so we have to do a first pass with a temporary different name, then change it back...
        if obj_id:
            category_data_temp = {"priority": priority, "name": category_name + "_TEMP"}
            category_json_temp = json.dumps(category_data_temp)
            while True:
                count += 1
                self.output(
                    "Category upload attempt {}".format(count), verbose_level=2,
                )
                r = http.put(url, headers=headers, data=category_json_temp, timeout=60)
                if r.status_code == 200:
                    self.output(
                        "Temporary category update successful. Waiting before updating again..."
                    )
                    sleep(2)
                    break
                if r.status_code == 409:
                    self.output(
                        "ERROR: Temporary category update failed due to a conflict"
                    )
                    break
                if count > 5:
                    self.output(
                        "ERROR: Temporary category update did not succeed after 5 attempts"
                    )
                    self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                    break
                sleep(10)

        # write the category. If updating an existing category, this reverts the name to its original.
        while True:
            count += 1
            self.output(
                "Category upload attempt {}".format(count), verbose_level=2,
            )
            if obj_id:
                r = http.put(url, headers=headers, data=category_json, timeout=60)
            else:
                r = http.post(url, headers=headers, data=category_json, timeout=60)
            if r.status_code == 201:
                self.output("Category created successfully")
                break
            if r.status_code == 200:
                self.output("Category update successful")
                break
            if r.status_code == 409:
                self.output("ERROR: Category creation failed due to a conflict")
                break
            if count > 5:
                self.output("ERROR: Category creation did not succeed after 5 attempts")
                self.output("\nHTTP POST Response Code: {}".format(r.status_code))
                break
            sleep(10)
        return r

    def main(self):
        """Do the main thing here"""
        self.jamf_url = self.env.get("JSS_URL")
        self.jamf_user = self.env.get("API_USERNAME")
        self.jamf_password = self.env.get("API_PASSWORD")
        self.category_name = self.env.get("category")
        self.priority = self.env.get("priority")

        # clear any pre-existing summary result
        if "jamfcategoryuploader_summary_result" in self.env:
            del self.env["jamfcategoryuploader_summary_result"]

        # encode the username and password into a basic auth b64 encoded string
        credentials = f"{self.jamf_user}:{self.jamf_password}"
        enc_creds_bytes = b64encode(credentials.encode("utf-8"))
        enc_creds = str(enc_creds_bytes, "utf-8")

        # now get the session token
        token = self.get_uapi_token(self.jamf_url, enc_creds)

        # now process the category
        # check for existing category
        self.output("\nChecking '{}' on {}".format(self.category_name, self.jamf_url))
        obj_id = self.get_uapi_obj_id_from_name(
            self.jamf_url, "categories", self.category_name, token
        )
        if obj_id:
            self.output(
                "Category '{}' already exists: ID {}".format(self.category_name, obj_id)
            )
            # PUT the category
            self.upload_category(
                self.jamf_url, self.category_name, self.priority, token, obj_id
            )
        else:
            # POST the category
            self.upload_category(
                self.jamf_url, self.category_name, self.priority, token
            )

        # output the summary
        self.env["category"] = self.category_name
        self.env["jamfcategoryuploader_summary_result"] = {
            "summary_text": "The following category was created or updated in Jamf Pro:",
            "report_fields": ["category", "priority"],
            "data": {"category": self.category_name, "priority": str(self.priority),},
        }


if __name__ == "__main__":
    PROCESSOR = JamfCategoryUploader()
    PROCESSOR.execute_shell()
