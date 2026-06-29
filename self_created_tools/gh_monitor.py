import requests
import json
import os
import argparse
from datetime import datetime

def get_pr_status(repo, pr_number, token=None):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching PR: {response.status_code} - {response.text}")
        return None

def get_pr_reviews(repo, pr_number, token=None):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching reviews: {response.status_code}")
        return []

def get_pr_comments(repo, pr_number, token=None):
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching comments: {response.status_code}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Monitor GitHub PR Status and Feedback")
    parser.add_argument("--repo", default="Job4874/jules-bridge", help="GitHub repository (owner/repo)")
    parser.add_argument("--pr", type=int, help="Pull Request number")
    parser.add_argument("--token", help="GitHub Personal Access Token (optional but recommended)")

    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")

    if not args.pr:
        # If no PR number, list open PRs
        url = f"https://api.github.com/repos/{args.repo}/pulls?state=open"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            prs = response.json()
            if not prs:
                print("No open PRs found.")
                return
            print(f"Open PRs for {args.repo}:")
            for pr in prs:
                print(f"#{pr['number']}: {pr['title']} ({pr['html_url']})")
        else:
            print(f"Error listing PRs: {response.status_code}")
        return

    pr_data = get_pr_status(args.repo, args.pr, token)
    if not pr_data:
        return

    print(f"--- PR #{args.pr}: {pr_data['title']} ---")
    print(f"Status: {pr_data['state']}")
    print(f"Mergeable: {pr_data.get('mergeable')}")
    print(f"Draft: {pr_data['draft']}")

    reviews = get_pr_reviews(args.repo, args.pr, token)
    if reviews:
        print("\n--- Reviews ---")
        for review in reviews:
            print(f"[{review['user']['login']}] {review['state']}: {review.get('body', '(no body)')}")

    comments = get_pr_comments(args.repo, args.pr, token)
    if comments:
        print("\n--- Comments ---")
        for comment in comments:
            print(f"[{comment['user']['login']}] at {comment['created_at']}: {comment['body'][:100]}...")

if __name__ == "__main__":
    main()
