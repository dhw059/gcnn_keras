import numpy as np
import scipy.sparse as sp



def precompute_adjacency_scaled(A,add_identity = True):
    """
    Precompute the scaled adjacency matrix A_scaled = D^-0.5 (A + I) D^-0.5.

    Args:
        A (np.array,scipy.sparse): Adjacency matrix of shape (N,N).
        add_identity (bool, optional): Whether to add identity. Defaults to True.

    Returns:
        np.array: D^-0.5 (A + I) D^-0.5.

    """
    if(isinstance(A,np.ndarray)):
        A = np.array(A,dtype=np.float)
        if(add_identity==True):
            A = A +  np.identity(A.shape[0])
        rowsum = np.sum(A,axis=-1)
        colsum = np.sum(A,axis=0)
        d_ii = np.power(rowsum, -0.5).flatten()
        d_jj = np.power(colsum, -0.5).flatten()
        d_ii[np.isinf(d_ii)] = 0.
        d_jj[np.isinf(d_jj)] = 0.
        Di = np.zeros((A.shape[0],A.shape[0]),dtype=A.dtype)
        Dj = np.zeros((A.shape[1],A.shape[1]),dtype=A.dtype)
        Di[np.arange(A.shape[0]),np.arange(A.shape[0])] = d_ii
        Dj[np.arange(A.shape[1]),np.arange(A.shape[1])] = d_jj
        return np.matmul(Di,np.matmul(A,Dj))
    elif(isinstance(A,sp.csr.csr_matrix) or
         isinstance(A,sp.coo.coo_matrix)):
        adj = sp.coo_matrix(A)
        if(add_identity==True):
            adj = adj + sp.eye(adj.shape[0])
        colsum = np.array(adj.sum(0))
        rowsum = np.array(adj.sum(1))
        d_ii = np.power(rowsum, -0.5).flatten()
        d_jj = np.power(colsum, -0.5).flatten()
        d_ii[np.isinf(d_ii)] = 0.
        d_jj[np.isinf(d_jj)] = 0.
        Di = sp.diags(d_ii,format='coo')
        Dj = sp.diags(d_jj,format='coo')
        return Di.dot(adj).dot(Dj).tocoo() 
    else:
        raise TypeError("Error: Matrix format not supported:",type(A))


def scaled_adjacency_to_list(Ascaled):
    """
    Map adjacency matrix to index list plus edge weights.

    Args:
        Ascaled (np.array,scipy.sparse): Scaled Adjacency matrix of shape (N,N). A_scaled = D^-0.5 (A + I) D^-0.5.

    Returns:
        edge_index (np.array): Indexlist of shape (N,2).
        edge_weight (np.array): Entries of Adjacency matrix of shape (N,N)
        
    """
    if(isinstance(Ascaled,np.ndarray)):
        A = np.array(Ascaled>0,dtype=np.bool)
        edge_weight = Ascaled[A]
        index1 = np.tile(np.expand_dims(np.arange(0,A.shape[0]),axis=1),(1,A.shape[1]))
        index2 = np.tile(np.expand_dims(np.arange(0,A.shape[1]),axis=0),(A.shape[0],1))
        index12 = np.concatenate([np.expand_dims(index1,axis=-1), np.expand_dims(index2,axis=-1)],axis=-1)
        edge_index = index12[A]
        return edge_index,edge_weight
    elif(isinstance(Ascaled,sp.csr.csr_matrix) or
         isinstance(Ascaled,sp.coo.coo_matrix)):
        Ascaled = Ascaled.tocoo()
        ei1 =  np.array(Ascaled.row.tolist(),dtype=np.int)
        ei2 =  np.array(Ascaled.col.tolist(),dtype=np.int)
        edge_index = np.concatenate([np.expand_dims(ei1,axis=-1),np.expand_dims(ei2,axis=-1)],axis=-1)
        edge_weight = np.array(Ascaled.data)
        return edge_index,edge_weight
    else:
        raise TypeError("Error: Matrix format not supported:",type(A))



def make_undirected(A):
    """
    Make adjacency matrix undirected. This adds edge if directed.

    Args:
        A (np.array,scipy.sparse): Adjacency matrix.

    Returns:
        A (np.array,scipy.sparse): undirected Adjacency matrix. This has A=A^T.

    """
    if(isinstance(A,np.ndarray)):
        At = np.transpose(A)
        Aout = (At>A)*At+(A>=At)*A
        return Aout
    elif(isinstance(A,sp.csr.csr_matrix) or
         isinstance(A,sp.coo.coo_matrix)):
        adj = sp.coo_matrix(A)
        adj_t = sp.coo_matrix(A).transpose()
        Aout = (adj_t>adj).multiply(adj_t)+(adj>adj_t).multiply(adj)+adj-(adj!=adj_t).multiply(adj)
        return Aout.tocoo()
         
