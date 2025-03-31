# Metamath2Py

Metamath2Py is a rewritten verifier that translates Metamath theorems into executable Python code.  
You can find detailed information about the project in the corresponding paper on arXiv: [link to paper].  

This project is based on the original Metamath verifier by David A. Wheeler, available here:  
[https://github.com/david-a-wheeler/mmverify.py](https://github.com/david-a-wheeler/mmverify.py)  

For more information about Metamath, visit the official Metamath website:  
[https://us.metamath.org/](https://us.metamath.org/)  

---

## Getting Started

This repository provides several entry points:

### **1. Get the Dataset of Python Files as Described in the Paper**

You have three options to obtain the dataset of Python files:

#### **Option 1: Generate a JSONL Dataset and Build Python Files**
1. Run `build_jsonl_dataset.py` to generate a JSON Lines dataset from a `set.mm` file.  
   **Note:** The `set.mm` file from [Metamath](https://github.com/metamath/set.mm) won't work directly, as proofs are stored in a compressed format.  
   Convert the proofs to an uncompressed format using the following commands:  
   ```plaintext
   save proof * /normal
   write source set_normal.mm
   ```
   *(Reference: [Metamath Google Group](https://groups.google.com/g/metamath/c/UJr6HtWkpYA))*  
   On an Intel Core i7, this process may take approximately 10 hours.

2. Then, run `build_dataset_of_python_files.py` to generate `.py` files containing theorems and proofs.  
   These files are designed to be executable and correct.

#### **Option 2: Use a Prebuilt JSONL Dataset**
1. Download a ready-to-use dataset in JSONL format from Hugging Face. [Metamath2Py on Hugginface, look for jsonl file](https://huggingface.co/datasets/kamushekp/Metamath2Py)
2. Run `build_dataset_of_python_files.py` to generate `.py` files containing theorems and proofs.

#### **Option 3 (RECOMMENDED): Download Prebuilt Python Files Directly**
1. You can download a ready-to-verify dataset consisting of thousands of Python files with theorems and their proofs.
[Metamath2Py on Hugginface, look for 7z archive](https://huggingface.co/datasets/kamushekp/Metamath2Py)
---

### **2. Verify Translated Files**

Once you have the `.py` files, run `verify_metamath2py_files.py` to verify all proof files.  
This process typically takes less than a minute on an Intel Core i7.

---

## License

Metamath2Py is open-source software released under the MIT license.