# Contributing Guide

Thank you for your interest in contributing to this project! This is a proof of concept and is not intended for production use. There are many limitations and edge cases that are not handled.
This repo will be updated from time to time to reflect the latest state of the migration tooling.

We welcome pull requests, bug reports, documentation improvements, and feature suggestions.

This repository is focused on **Ansible Automation Platform (AAP) 2.4 → 2.5 migration automation**, and contributions should align with that mission.

---

## ✅ How to Contribute

You can contribute in several ways:

- 🐛 Reporting bugs
- ✨ Suggesting new features
- 📝 Improving documentation
- 🔧 Submitting code changes
- ✅ Adding tests or validation logic

---

## 🐛 Reporting Bugs

Before opening a bug report:

1. **Search existing issues** to avoid duplicates.
2. Make sure you are using the **latest version** of the code.
3. Gather:
   - A clear description of the issue
   - Relevant logs or error messages (redact secrets!)
   - Steps to reproduce
   - Your environment:
     - OS
     - Python version
     - Ansible version
     - AAP version

### Bug Report Template

When opening an issue, please include:

- **Description**
- **Expected behavior**
- **Actual behavior**
- **Steps to reproduce**
- **Logs/output (with secrets removed)**
- **Environment details**

---

## ✨ Feature Requests

We welcome feature ideas! When submitting a feature request:

- Clearly describe the **problem you are trying to solve**
- Explain **why existing behavior is insufficient**
- Provide **examples or use cases**
- If possible, propose an **implementation approach**

---

## 🔧 Contributing Code

### 1. Fork the Repository

```bash
git fork <repo-url>
git clone <your-fork-url>
cd <repo>