from time import perf_counter
import multiprocessing as mp
import os

from functions import classify, get_file_names, load_transactions_from_csv, simplify, profile

if __name__ == '__main__':
    num_processes = mp.cpu_count()
    pool = mp.Pool(processes=num_processes)
    print(f'found {num_processes} available threads\n')

    csv_file_directory = '../csv_files/'
    input_directory = f'{csv_file_directory}raw_transactions_classified/'
    output_directory = f'{csv_file_directory}simplified_transactions/'

    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    csv_file_names = get_file_names(input_directory, "[0-9]{4}-[0-9]{2}-[0-9]{2}.csv$")

    for file_name in csv_file_names:
        simp_start = perf_counter()

        print(f'processing file {input_directory}{file_name}:\n')
        print('    loading transactions... ', end='', flush=True)
        transactions = load_transactions_from_csv(f'{input_directory}{file_name}')
        print('done')

        temp = profile(transactions)
        for (key, val) in temp.items():
            print(f'        {key:>14}: {val:,}')
        print()

        print(f'    simplifying transactions... ', end='', flush=True)
        simplified_transactions = pool.map(simplify, transactions)
        print(f'done')

        print(f'    reclassifying simplifed transactions... ', end='', flush=True)
        for index, tx in enumerate(simplified_transactions):
            if tx.type == 'unclassified':
                simplified_transactions[index] = classify(tx)
        print('done')

        temp = profile(simplified_transactions)
        for (key, val) in temp.items():
            print(f'        {key:>14}: {val:,}')
        print()

        print(f'    writing new csv file {output_directory}{file_name}... ', end='', flush=True)
        with open(f'{output_directory}{file_name}', 'w') as output_file:
            output_file.write('transaction_hash,num_inputs,input_addresses,input_values,num_outputs,output_addresses,output_values,transaction_fee,transaction_class\n')
            for transaction in simplified_transactions:
                output_file.write(transaction.to_csv_string())
        print('done')

        simp_end = perf_counter()
        print(f'    finished in {simp_end - simp_start:.2f}s\n')
